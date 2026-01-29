from PIL import Image
from collections import Counter

# Load the logo
img = Image.open('static/img/logo.png')
img = img.convert('RGB')

# Get the dominant colors
pixels = list(img.getdata())
color_counts = Counter(pixels)

# Filter out very light/white colors (greater than 240)
filtered_colors = [(color, count) for color, count in color_counts.items() 
                   if not (color[0] > 240 and color[1] > 240 and color[2] > 240)]

top_colors = sorted(filtered_colors, key=lambda x: x[1], reverse=True)[:10]

print('Top 10 meaningful colors in logo (RGB):')
for i, (color, count) in enumerate(top_colors, 1):
    r, g, b = color
    hex_color = '#{:02x}{:02x}{:02x}'.format(r, g, b)
    print(f'{i}. RGB{color} = {hex_color} (count: {count})')

