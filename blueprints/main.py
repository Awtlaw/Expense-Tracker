from flask import Blueprint, render_template, request, redirect, session, flash, url_for, Response
from datetime import datetime, timedelta
from cs50 import SQL
from io import BytesIO
from fpdf import FPDF
from helpers import validate_password, sanitize_text
from werkzeug.security import check_password_hash, generate_password_hash
import os

db = SQL(os.getenv("DATABASE_URL", "sqlite:///database.db"))

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    return render_template("landing.html", current_year=datetime.now().year)

@main_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    try:
        income_total = db.execute("SELECT SUM(amount) AS total FROM income WHERE user_id = ?", user_id)[0]["total"] or 0
        expense_total = db.execute("SELECT SUM(amount) AS total FROM expenses WHERE user_id = ?", user_id)[0]["total"] or 0
        balance = income_total - expense_total

        current_month = datetime.now().strftime("%Y-%m")
        income_month = db.execute("SELECT SUM(amount) AS total FROM income WHERE user_id = ? AND strftime('%Y-%m', date) = ?", user_id, current_month)[0]["total"] or 0
        expenses_month = db.execute("SELECT SUM(amount) AS total FROM expenses WHERE user_id = ? AND strftime('%Y-%m', date) = ?", user_id, current_month)[0]["total"] or 0

        categories = db.execute("SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category", user_id)
        expense_categories = [row["category"] for row in categories] if categories else []
        expense_amounts = [row["total"] for row in categories] if categories else []

        # Get budget data
        budgets_result = db.execute("SELECT category, budget_limit FROM budgets WHERE user_id = ? AND month = ?", user_id, current_month)
        budgets = budgets_result if budgets_result and isinstance(budgets_result, list) else []
        budget_warnings = []
        budget_data = []
        
        # Get total monthly budget
        total_budget_result = db.execute(
            "SELECT budget_limit FROM budgets WHERE user_id = ? AND month = ? AND category = 'TOTAL_MONTHLY'",
            user_id, current_month
        )
        total_budget_limit = None
        if total_budget_result and isinstance(total_budget_result, list) and len(total_budget_result) > 0:
            total_budget_limit = total_budget_result[0]["budget_limit"]
        total_budget_warning = None
        
        if total_budget_limit:
            if expenses_month > total_budget_limit:
                total_budget_warning = {
                    "limit": total_budget_limit,
                    "spent": expenses_month,
                    "exceeded": expenses_month - total_budget_limit
                }
        
        for budget in budgets:
            category = budget["category"]
            if category == "TOTAL_MONTHLY":
                continue
            limit = budget["budget_limit"]
            spent = db.execute("SELECT SUM(amount) AS total FROM expenses WHERE user_id = ? AND category = ? AND strftime('%Y-%m', date) = ?", 
                             user_id, category, current_month)[0]["total"] or 0
            percentage = (spent / limit * 100) if limit > 0 else 0
            
            budget_data.append({
                "category": category,
                "limit": limit,
                "spent": spent,
                "remaining": max(0, limit - spent),
                "percentage": min(percentage, 100),
                "is_exceeded": spent > limit
            })
            
            if spent > limit:
                budget_warnings.append({
                    "category": category,
                    "limit": limit,
                    "spent": spent,
                    "exceeded": spent - limit
                })

        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        income_data = [1000, 1200, 1500, 1300, 1100, 1600]
        expenses_data = [500, 700, 800, 600, 500, 900]

        return render_template(
            "dashboard.html",
            balance=balance,
            income_month=income_month,
            expenses_month=expenses_month,
            expense_categories=expense_categories,
            expense_amounts=expense_amounts,
            months=months,
            income_data=income_data,
            expenses_data=expenses_data,
            budget_warnings=budget_warnings,
            budget_data=budget_data,
            total_budget_limit=total_budget_limit,
            total_budget_warning=total_budget_warning,
            current_year=datetime.now().year
        )
    except Exception as e:
        import traceback
        error_msg = f"Error loading dashboard: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        flash(f"Error loading dashboard: {str(e)}")
        return redirect(url_for("auth.login"))


@main_bp.route("/reports")
def reports():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    now = datetime.now()

    try:
        current_month = now.strftime("%Y-%m")
        last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        current_year = now.strftime("%Y")

        weekly_expenses = db.execute(
            "SELECT SUM(amount) AS total FROM expenses WHERE user_id = ? AND date >= date('now','-7 days')",
            user_id
        )[0]["total"] or 0

        monthly_expenses = db.execute(
            "SELECT SUM(amount) AS total FROM expenses WHERE user_id = ? AND strftime('%Y-%m', date) = ?",
            user_id, current_month
        )[0]["total"] or 0

        yearly_expenses = db.execute(
            "SELECT SUM(amount) AS total FROM expenses WHERE user_id = ? AND strftime('%Y', date) = ?",
            user_id, current_year
        )[0]["total"] or 0

        last_month_expenses = db.execute(
            "SELECT SUM(amount) AS total FROM expenses WHERE user_id = ? AND strftime('%Y-%m', date) = ?",
            user_id, last_month
        )[0]["total"] or 0

        month_change = monthly_expenses - last_month_expenses

        categories = db.execute(
            "SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC",
            user_id
        )

        category_labels = [row["category"] for row in categories]
        category_totals = [row["total"] for row in categories]
        top_category = category_labels[0] if category_labels else "N/A"

        return render_template(
            "reports.html",
            weekly_expenses=weekly_expenses,
            monthly_expenses=monthly_expenses,
            yearly_expenses=yearly_expenses,
            last_month_expenses=last_month_expenses,
            month_change=month_change,
            top_category=top_category,
            category_labels=category_labels,
            category_totals=category_totals,
            current_year=current_year
        )
    except Exception as e:
        flash(f"Error loading reports: {str(e)}")
        return redirect(url_for("main.dashboard"))


@main_bp.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    try:
        user = db.execute("SELECT username, email, created_at FROM users WHERE id = ?", user_id)[0]

        total_income = db.execute(
            "SELECT SUM(amount) AS total FROM income WHERE user_id = ?", user_id
        )[0]["total"] or 0

        total_expenses = db.execute(
            "SELECT SUM(amount) AS total FROM expenses WHERE user_id = ?", user_id
        )[0]["total"] or 0

        balance = total_income - total_expenses

        # Get total monthly budget
        current_month = datetime.now().strftime("%Y-%m")
        total_budget_result = db.execute(
            "SELECT budget_limit FROM budgets WHERE user_id = ? AND month = ? AND category = 'TOTAL_MONTHLY'",
            user_id, current_month
        )
        total_monthly_budget = total_budget_result[0]["budget_limit"] if total_budget_result else None
        
        # Get budget suggestions
        three_months_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        categories_data = db.execute(
            """SELECT category, AVG(monthly_total) as avg_spent 
               FROM (
                   SELECT category, strftime('%Y-%m', date) as month, SUM(amount) as monthly_total
                   FROM expenses 
                   WHERE user_id = ? AND date >= ?
                   GROUP BY category, month
               )
               GROUP BY category
            """,
            user_id, three_months_ago
        )
        
        budget_suggestions = []
        for row in categories_data:
            category = row["category"]
            avg_spent = row["avg_spent"] or 0
            suggested_budget = round(avg_spent * 1.15, 2)
            
            existing = db.execute(
                "SELECT budget_limit FROM budgets WHERE user_id = ? AND category = ? AND month = ?",
                user_id, category, current_month
            )
            
            budget_suggestions.append({
                "category": category,
                "avg_spent": round(avg_spent, 2),
                "suggested": suggested_budget,
                "has_budget": len(existing) > 0
            })

        return render_template(
            "profile.html",
            user=user,
            total_income=total_income,
            total_expenses=total_expenses,
            balance=balance,
            total_monthly_budget=total_monthly_budget,
            budget_suggestions=budget_suggestions,
            current_year=datetime.now().year
        )
    except Exception as e:
        flash(f"Error loading profile: {str(e)}")
        return redirect(url_for("main.dashboard"))


@main_bp.route("/change_password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirmation = request.form.get("confirmation", "")

    if not current_password or not new_password or not confirmation:
        flash("All fields are required.")
        return redirect(url_for("main.profile"))

    if new_password != confirmation:
        flash("New passwords do not match.")
        return redirect(url_for("main.profile"))

    is_valid, msg = validate_password(new_password)
    if not is_valid:
        flash(msg)
        return redirect(url_for("main.profile"))

    try:
        user = db.execute("SELECT hash FROM users WHERE id = ?", user_id)[0]

        if not check_password_hash(user["hash"], current_password):
            flash("Current password is incorrect.")
            return redirect(url_for("main.profile"))

        new_hash = generate_password_hash(new_password)
        db.execute("UPDATE users SET hash = ? WHERE id = ?", new_hash, user_id)
        flash("Password changed successfully!")
    except Exception as e:
        flash(f"Error changing password: {str(e)}")

    return redirect(url_for("main.profile"))


@main_bp.route("/export_pdf")
def export_pdf():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    try:
        expenses = db.execute("SELECT date, category, amount, note FROM expenses WHERE user_id = ? ORDER BY date DESC", user_id)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Expense Report", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(40, 10, "Date", 1)
        pdf.cell(50, 10, "Category", 1)
        pdf.cell(30, 10, "Amount", 1)
        pdf.cell(70, 10, "Note", 1)
        pdf.ln()

        pdf.set_font("Arial", "", 12)
        for exp in expenses:
            pdf.cell(40, 10, exp["date"], 1)
            pdf.cell(50, 10, exp["category"], 1)
            pdf.cell(30, 10, f"${exp['amount']:,.2f}", 1)
            pdf.cell(70, 10, exp["note"][:35] if exp["note"] else "", 1)
            pdf.ln()

        output = BytesIO()
        pdf.output(output)
        output.seek(0)

        return Response(output, mimetype="application/pdf",
                        headers={"Content-Disposition": "attachment; filename=expenses.pdf"})
    except Exception as e:
        flash(f"Error generating PDF: {str(e)}")
        return redirect(url_for("main.dashboard"))


@main_bp.route("/set_budget", methods=["POST"])
def set_budget():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    category = request.form.get("category", "").strip()
    budget_limit = request.form.get("budget_limit", "")
    
    if not category or not budget_limit:
        flash("Category and budget limit are required")
        return redirect(url_for("main.profile"))
    
    try:
        budget_limit = float(budget_limit)
        if budget_limit <= 0:
            flash("Budget limit must be greater than 0")
            return redirect(url_for("main.profile"))
        
        current_month = datetime.now().strftime("%Y-%m")
        db.execute(
            "INSERT OR REPLACE INTO budgets (user_id, category, budget_limit, month) VALUES (?, ?, ?, ?)",
            user_id, category, budget_limit, current_month
        )
        flash(f"Budget set for {category}: ${budget_limit:.2f}")
    except ValueError:
        flash("Invalid budget amount")
    except Exception as e:
        flash(f"Error setting budget: {str(e)}")
    
    return redirect(url_for("main.profile"))


@main_bp.route("/set_total_budget", methods=["POST"])
def set_total_budget():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    total_limit = request.form.get("total_budget", "")
    
    if not total_limit:
        flash("Total monthly budget is required")
        return redirect(url_for("main.profile"))
    
    try:
        total_limit = float(total_limit)
        if total_limit <= 0:
            flash("Budget limit must be greater than 0")
            return redirect(url_for("main.profile"))
        
        current_month = datetime.now().strftime("%Y-%m")
        db.execute(
            "INSERT OR REPLACE INTO budgets (user_id, category, budget_limit, month) VALUES (?, ?, ?, ?)",
            user_id, "TOTAL_MONTHLY", total_limit, current_month
        )
        flash(f"Total monthly budget set to ${total_limit:.2f}")
    except ValueError:
        flash("Invalid budget amount")
    except Exception as e:
        flash(f"Error setting budget: {str(e)}")
    
    return redirect(url_for("main.profile"))


@main_bp.route("/set_budgets_bulk", methods=["POST"])
def set_budgets_bulk():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    current_month = datetime.now().strftime("%Y-%m")
    
    try:
        # Get all budget amounts from form
        budgets = request.form
        count = 0
        
        for key, value in budgets.items():
            if key.startswith("budget_") and value:
                category = key.replace("budget_", "")
                try:
                    budget_limit = float(value)
                    if budget_limit > 0:
                        db.execute(
                            "INSERT OR REPLACE INTO budgets (user_id, category, budget_limit, month) VALUES (?, ?, ?, ?)",
                            user_id, category, budget_limit, current_month
                        )
                        count += 1
                except ValueError:
                    continue
        
        flash(f"Successfully set {count} budget(s)!")
    except Exception as e:
        flash(f"Error setting budgets: {str(e)}")
    
    return redirect(url_for("main.profile"))


@main_bp.route("/get_budgets")
def get_budgets():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    current_month = datetime.now().strftime("%Y-%m")
    
    try:
        budgets = db.execute(
            "SELECT category, budget_limit FROM budgets WHERE user_id = ? AND month = ?",
            user_id, current_month
        )
        return {
            "budgets": budgets
        }
    except Exception as e:
        flash(f"Error loading budgets: {str(e)}")
        return {"budgets": []}


@main_bp.route("/get_budget_suggestions")
def get_budget_suggestions():
    if "user_id" not in session:
        return {"suggestions": []}

    user_id = session["user_id"]
    
    try:
        # Get all categories from last 3 months of expenses
        three_months_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        
        categories_data = db.execute(
            """SELECT category, AVG(monthly_total) as avg_spent 
               FROM (
                   SELECT category, strftime('%Y-%m', date) as month, SUM(amount) as monthly_total
                   FROM expenses 
                   WHERE user_id = ? AND date >= ?
                   GROUP BY category, month
               )
               GROUP BY category
            """,
            user_id, three_months_ago
        )
        
        suggestions = []
        for row in categories_data:
            category = row["category"]
            avg_spent = row["avg_spent"] or 0
            # Suggest 15% above average
            suggested_budget = round(avg_spent * 1.15, 2)
            
            # Check if budget already exists
            existing = db.execute(
                "SELECT budget_limit FROM budgets WHERE user_id = ? AND category = ? AND month = ?",
                user_id, category, datetime.now().strftime("%Y-%m")
            )
            
            suggestions.append({
                "category": category,
                "avg_spent": round(avg_spent, 2),
                "suggested": suggested_budget,
                "has_budget": len(existing) > 0
            })
        
        return {"suggestions": suggestions}
    except Exception as e:
        return {"suggestions": [], "error": str(e)}


@main_bp.route("/budgets")
def budgets_page():
    """Display all per-category budgets for the current month"""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    user_id = session["user_id"]
    current_month = datetime.now().strftime("%Y-%m")
    
    try:
        # Get all per-category budgets
        budgets = db.execute(
            "SELECT id, category, budget_limit FROM budgets WHERE user_id = ? AND month = ? AND category != 'TOTAL_MONTHLY' ORDER BY category",
            user_id, current_month
        )
        budgets = budgets if budgets else []
        
        # Get expenses for each budget category to show progress
        budget_data = []
        for budget in budgets:
            spent = db.execute(
                "SELECT SUM(amount) AS total FROM expenses WHERE user_id = ? AND category = ? AND strftime('%Y-%m', date) = ?",
                user_id, budget["category"], current_month
            )[0]["total"] or 0
            
            budget_data.append({
                "id": budget["id"],
                "category": budget["category"],
                "limit": budget["budget_limit"],
                "spent": spent,
                "remaining": max(0, budget["budget_limit"] - spent),
                "percentage": min((spent / budget["budget_limit"] * 100) if budget["budget_limit"] > 0 else 0, 100),
                "is_exceeded": spent > budget["budget_limit"]
            })
        
        return render_template(
            "budgets.html",
            budget_data=budget_data,
            current_month=current_month,
            current_year=datetime.now().year
        )
    except Exception as e:
        flash(f"Error loading budgets: {str(e)}")
        return redirect(url_for("main.dashboard"))


@main_bp.route("/delete_budget/<int:budget_id>", methods=["POST"])
def delete_budget(budget_id):
    """Delete a budget"""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    user_id = session["user_id"]
    
    try:
        # Verify the budget belongs to the user
        budget = db.execute("SELECT user_id FROM budgets WHERE id = ?", budget_id)
        if not budget or budget[0]["user_id"] != user_id:
            flash("Budget not found")
            return redirect(url_for("main.budgets_page"))
        
        # Delete the budget
        db.execute("DELETE FROM budgets WHERE id = ?", budget_id)
        flash("Budget deleted successfully")
        return redirect(url_for("main.budgets_page"))
    except Exception as e:
        flash(f"Error deleting budget: {str(e)}")
        return redirect(url_for("main.budgets_page"))