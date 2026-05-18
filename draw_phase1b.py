import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon


def rbox(ax, cx, cy, w, h, fc, ec='#1f2a73', lw=1.8, r=0.12, z=2):
    patch = FancyBboxPatch(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle=f"round,pad={r}",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
        zorder=z,
    )
    ax.add_patch(patch)
    return patch


def arrow(ax, x1, y1, x2, y2, color='#5f6bc3', lw=1.8, curve=0.0):
    ax.annotate(
        '',
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle='-|>',
            color=color,
            lw=lw,
            connectionstyle=f'arc3,rad={curve}',
            shrinkA=0,
            shrinkB=0,
        ),
        zorder=6,
    )


def draw_hash_vector(ax, x, y, colors):
    w = 0.17
    h = 0.22
    gap = 0.01
    for i, c in enumerate(colors):
        rect = Rectangle((x + i * (w + gap), y), w, h, facecolor=c, edgecolor='#24418e', linewidth=0.7, zorder=4)
        ax.add_patch(rect)


fig, ax = plt.subplots(figsize=(14, 7.2), dpi=150)
fig.patch.set_facecolor('#efefef')
ax.set_facecolor('#efefef')
ax.set_xlim(0, 14)
ax.set_ylim(0, 7.2)
ax.axis('off')

# Title
ax.plot([0.5, 13.5], [6.3, 6.3], color='#323a8b', lw=1.4)
ax.plot([0.5, 0.5], [6.8, 6.1], color='#323a8b', lw=1.4)
ax.text(0.62, 6.52, 'Phase 1B: Semantic Hash Indexing', fontsize=24, fontweight='bold', color='#323a8b', va='center')

# Left semantic hash input
ax.text(0.76, 4.12, 'Semantic Hash', fontsize=12.5, color='#161616', ha='center')
ax.text(0.64, 3.86, r'$h_i$', fontsize=16, color='#161616', ha='center', style='italic')

outer = Rectangle((0.25, 2.15), 0.82, 1.58, facecolor='none', edgecolor='#666', linewidth=0.8, linestyle='--', zorder=3)
ax.add_patch(outer)

draw_hash_vector(ax, 0.34, 3.45, ['#c6d4f7', '#9fb4ed', '#c6d4f7', '#9fb4ed'])
draw_hash_vector(ax, 0.34, 3.05, ['#ead8d2', '#ead8d2', '#c6d4f7', '#e7eef8'])
draw_hash_vector(ax, 0.34, 2.65, ['#e7eef8', '#c5d6ef', '#d6efd6', '#e7eef8'])
draw_hash_vector(ax, 0.34, 2.25, ['#e7eef8', '#c5d6ef', '#e7eef8', '#b8d1ef'])

# Hash function block
rbox(ax, 2.2, 2.95, 1.8, 0.92, fc='#e8ecff', ec='#5f6bc3', lw=1.8, r=0.08, z=2)
ax.text(2.2, 3.08, 'Hash Function', fontsize=11, fontweight='bold', color='#253180', ha='center')
ax.text(2.2, 2.84, r'$g(h_i)$', fontsize=13, color='#253180', ha='center')
ax.text(2.2, 2.62, 'bucket_id = 0110', fontsize=9, color='#4958b8', ha='center')

# Main panels
rbox(ax, 4.45, 3.2, 2.35, 4.2, fc='#ece9da', ec='none', lw=0, r=0.25, z=1)
rbox(ax, 8.05, 3.2, 2.35, 4.2, fc='#ece9da', ec='none', lw=0, r=0.25, z=1)

ax.text(4.45, 4.95, 'Hash Index Drawers', fontsize=12, color='#111', ha='center')
ax.text(8.05, 4.95, 'Candidate Cases', fontsize=12, color='#111', ha='center')

# Drawers inside index panel
left = 3.45
right = 5.45
y0 = 4.55
drawer_h = 0.45
gap = 0.14
labels = ['bucket 0101  size=18', 'bucket 0110  size=23', 'bucket 0111  size=11', 'bucket 1010  size=29', 'bucket 1110  size=7']
for i, label in enumerate(labels):
    y = y0 - i * (drawer_h + gap)
    is_target = i == 1
    fc = '#fffaf0' if is_target else '#f8f4e8'
    ec = '#d87a1d' if is_target else '#b7aa8b'
    lw = 2.0 if is_target else 1.1
    drawer = FancyBboxPatch((left, y), right - left, drawer_h, boxstyle='round,pad=0.03', facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3)
    ax.add_patch(drawer)
    handle = Rectangle((right - 0.16, y + drawer_h / 2 - 0.06), 0.07, 0.12, facecolor='#8b7d62', edgecolor='none', zorder=4)
    ax.add_patch(handle)
    ax.text(left + 0.1, y + drawer_h / 2, label, fontsize=8.8, color='#3f3a2f', ha='left', va='center', zorder=4)

ax.text(4.45, 1.2, 'Inverted index by hash bucket', fontsize=9, color='#7c735f', ha='center', style='italic')

# Candidate cards
cards = [
    ('case_1023', 'score: 0.91', '#f7efe8', '#c6702b'),
    ('case_2451', 'score: 0.87', '#f2ecfa', '#7a5ab0'),
    ('case_3308', 'score: 0.82', '#eaf3fb', '#3c74a7'),
    ('case_4022', 'score: 0.79', '#edf7ed', '#4c8e4c'),
]
cy = 4.45
for i, (cid, sc, fc, ec) in enumerate(cards):
    y = cy - i * 0.62
    card = FancyBboxPatch((7.2, y), 1.7, 0.44, boxstyle='round,pad=0.05', facecolor=fc, edgecolor=ec, linewidth=1.2, zorder=3)
    ax.add_patch(card)
    ax.text(7.3, y + 0.3, cid, fontsize=9.2, fontweight='bold', color='#2f2f2f', ha='left', va='center')
    ax.text(8.56, y + 0.3, sc, fontsize=8.5, color='#4a4a4a', ha='right', va='center')

ax.text(8.05, 1.2, 'Retrieve candidate case IDs', fontsize=9, color='#7c735f', ha='center', style='italic')

# Flow arrows
arrow(ax, 1.07, 2.95, 1.3, 2.95)
arrow(ax, 1.3, 2.95, 3.3, 2.95)
arrow(ax, 5.65, 2.95, 6.85, 2.95)

# Near-bucket expansion (dashed)
arrow(ax, 5.2, 3.95, 7.0, 4.78, color='#b25d3b', lw=1.3, curve=0.15)
ax.lines[-1].set_linestyle('--') if ax.lines else None
ax.text(6.2, 4.94, 'Hamming radius = 1', fontsize=8.7, color='#b25d3b', ha='center')

# Extra labels
ax.text(6.25, 2.6, 'target bucket -> candidate pool', fontsize=9, color='#666', ha='center')

# Bottom baseline
ax.plot([0.45, 13.5], [0.2, 0.2], color='#323a8b', lw=1.4)

out = '/home/aru/AI_LAW/image copy.png'
plt.tight_layout(pad=0.2)
plt.savefig(out, dpi=150, bbox_inches='tight', facecolor='#efefef')
print(f'Done -> {out}')
