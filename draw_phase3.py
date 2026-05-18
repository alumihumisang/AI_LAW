import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Polygon
import numpy as np

fig, ax = plt.subplots(figsize=(20, 12))
ax.set_xlim(0, 20)
ax.set_ylim(0, 12)
ax.axis('off')
fig.patch.set_facecolor('#f5f7fa')
ax.set_facecolor('#f5f7fa')

def rbox(cx, cy, w, h, fc, ec='white', lw=2, radius=0.2, zorder=2, alpha=1.0):
    box = FancyBboxPatch((cx-w/2, cy-h/2), w, h,
                         boxstyle=f"round,pad={radius}",
                         facecolor=fc, edgecolor=ec, linewidth=lw,
                         alpha=alpha, zorder=zorder)
    ax.add_patch(box)

def arr(x1, y1, x2, y2, color='#777', lw=2, curve=0):
    cs = f'arc3,rad={curve}'
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                connectionstyle=cs, mutation_scale=18), zorder=5)

def diamond(cx, cy, hw, hh, fc, ec, lw=2):
    pts = [[cx, cy+hh],[cx+hw, cy],[cx, cy-hh],[cx-hw, cy]]
    poly = Polygon(pts, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3)
    ax.add_patch(poly)

def txt(x, y, t, fs=10, fw='normal', color='#222', ha='center', va='center',
        z=6, style='normal'):
    ax.text(x, y, t, fontsize=fs, fontweight=fw, color=color,
            ha=ha, va=va, zorder=z, style=style)

# ─── TITLE ─────────────────────────────────────────────────────────────────
txt(10, 11.55, 'Phase 3: Query-Time Retrieval', fs=23, fw='bold', color='#1a3a5c')
ax.plot([0.4, 19.6], [11.1, 11.1], color='#1a3a5c', lw=2.5)

TOP_Y    = 8.5    # main flow y-centre
BOX_H    = 3.2    # height of main boxes
SPARSE_Y = 5.0    # PARENT_OF box y-centre
LEG_Y    = 2.2    # legend y-centre

# ══════════════════════════════════════════════════════════════════════════
# STEP 1: New Case  (cx=2.2)
# ══════════════════════════════════════════════════════════════════════════
rbox(2.2, TOP_Y, 3.4, BOX_H, '#dce8f5', ec='#5b9bd5', lw=2.5)
txt(2.2, 9.75, 'New Case', fs=15, fw='bold', color='#154360')
txt(2.2, 9.25, '(query input)', fs=9.5, color='#5b9bd5', style='italic')

sq_data = [
    (0.65, '#c0392b', 'Fact=A',   'DUI'),
    (1.85, '#27ae60', 'Injury=C', 'Fracture'),
    (3.05, '#2980b9', 'Comp=C',   '~80 wan'),
]
for sx, c, lbl, sub in sq_data:
    sq = FancyBboxPatch((sx-0.52, TOP_Y-0.72), 1.04, 0.65,
                         boxstyle="round,pad=0.07",
                         facecolor=c, edgecolor='white', lw=1.5, alpha=0.9, zorder=4)
    ax.add_patch(sq)
    txt(sx, TOP_Y-0.4, lbl, fs=8.5, fw='bold', color='white', z=5)
    txt(sx, TOP_Y-1.12, sub, fs=8, color=c)

# ─── Arrow 1 ───────────────────────────────────────────────────────────────
arr(3.9, TOP_Y, 5.0, TOP_Y, color='#888', lw=2, curve=0)
txt(4.45, TOP_Y+0.45, 'Boolean\nVector', fs=8.5, color='#888')

# ══════════════════════════════════════════════════════════════════════════
# STEP 2: Bucket Lookup  (cx=6.6)
# ══════════════════════════════════════════════════════════════════════════
rbox(6.6, TOP_Y, 3.1, BOX_H, '#d5f5e3', ec='#1e8449', lw=2.5)
txt(6.6, 9.75, 'Bucket Lookup', fs=15, fw='bold', color='#145a32')
txt(6.6, 9.25, '(Neo4j query)', fs=9.5, color='#1e8449', style='italic')
txt(6.6, 8.7, 'bucket_id =', fs=10, color='#145a32')
ax.text(6.6, 8.15, '"A . C . C"', fontsize=12, ha='center', color='#145a32',
        fontfamily='monospace', fontweight='bold', zorder=5)
txt(6.6, 7.55, 'Found  N  matching cases', fs=9.5, color='#1e8449', fw='bold')

# ─── Arrow 2 ───────────────────────────────────────────────────────────────
arr(8.15, TOP_Y, 9.15, TOP_Y, color='#888', lw=2, curve=0)

# ══════════════════════════════════════════════════════════════════════════
# DECISION DIAMOND  (cx=10.3)
# ══════════════════════════════════════════════════════════════════════════
diamond(10.3, TOP_Y, 1.2, 0.88, '#fdebd0', '#e67e22', lw=2.5)
txt(10.3, TOP_Y+0.2, 'N >= k ?', fs=11.5, fw='bold', color='#784212')
txt(10.3, TOP_Y-0.25, 'enough?', fs=9, color='#9a6420')

# ─── YES arrow ─────────────────────────────────────────────────────────────
arr(11.5, TOP_Y, 12.6, TOP_Y, color='#1e8449', lw=2.5, curve=0)
txt(12.05, TOP_Y+0.45, 'Yes', fs=11, fw='bold', color='#1e8449')

# ─── NO arrow (down to PARENT_OF) ──────────────────────────────────────────
arr(10.3, TOP_Y-0.88, 10.3, SPARSE_Y+0.88, color='#c0392b', lw=2.5, curve=0)
txt(11.0, (TOP_Y-0.88 + SPARSE_Y+0.88)/2, 'No\n(sparse)', fs=10,
    fw='bold', color='#c0392b')

# ══════════════════════════════════════════════════════════════════════════
# STEP 3A: PARENT_OF Traversal  (cx=10.3, y=SPARSE_Y)
# ══════════════════════════════════════════════════════════════════════════
rbox(10.3, SPARSE_Y, 5.4, 1.9, '#fadbd8', ec='#c0392b', lw=2.5)
txt(10.3, SPARSE_Y+0.65, 'Traverse  PARENT_OF', fs=13.5, fw='bold', color='#922b21')
txt(10.3, SPARSE_Y+0.12, 'Walk to higher-severity bucket', fs=10.5, color='#922b21')
txt(10.3, SPARSE_Y-0.4, '(borrow neighbor cases to fill candidate pool)',
    fs=9, color='#c0392b', style='italic')

# mini DAG inside: Cp -> Ci -> leaf
node_pos = [(8.35, SPARSE_Y+0.25), (9.1, SPARSE_Y+0.25), (9.75, SPARSE_Y-0.22)]
for i, (nx, ny) in enumerate(node_pos):
    circ = plt.Circle((nx, ny), 0.27, color='#c0392b', alpha=0.72, zorder=6)
    ax.add_patch(circ)
    lbl = ['Cp', 'Ci', ''][i]
    txt(nx, ny, lbl, fs=8.5, fw='bold', color='white', z=7)
ax.annotate('', xy=(8.83, SPARSE_Y+0.25), xytext=(8.62, SPARSE_Y+0.25),
            arrowprops=dict(arrowstyle='->', color='#e74c3c', lw=1.6), zorder=7)
ax.annotate('', xy=(9.51, SPARSE_Y-0.07), xytext=(9.27, SPARSE_Y+0.1),
            arrowprops=dict(arrowstyle='->', color='#e74c3c', lw=1.6), zorder=7)

# ─── Curved arrow: PARENT_OF → Score Ranking ──────────────────────────────
arr(13.0, SPARSE_Y+0.2, 14.6, TOP_Y-1.6, color='#c0392b', lw=2.2, curve=-0.28)
txt(14.35, 6.35, 'augmented\ncandidate pool', fs=9.5, color='#c0392b')

# ══════════════════════════════════════════════════════════════════════════
# STEP 3B: Score Ranking  (cx=14.7)
# ══════════════════════════════════════════════════════════════════════════
rbox(14.7, TOP_Y, 3.2, BOX_H, '#fef9e7', ec='#d4ac0d', lw=2.5)
txt(14.7, 9.75, 'Score Ranking', fs=15, fw='bold', color='#7d6608')
txt(14.7, 9.25, '(sort candidates)', fs=9.5, color='#b7950b', style='italic')
ax.text(14.7, 8.65, r'Score = $\alpha \cdot S_F + \beta \cdot S_I$',
        fontsize=11.5, ha='center', color='#7d6608', style='italic', zorder=5)
ax.text(14.7, 8.08, r'$+ (1{-}\alpha{-}\beta) \cdot S_C$',
        fontsize=11.5, ha='center', color='#7d6608', style='italic', zorder=5)
txt(14.7, 7.5, '^ higher score ranked first', fs=9.5, color='#b7950b', fw='bold')

# ─── Arrow → Top-K ─────────────────────────────────────────────────────────
arr(16.3, TOP_Y, 17.2, TOP_Y, color='#888', lw=2, curve=0)

# ══════════════════════════════════════════════════════════════════════════
# STEP 4: Top-K Results  (cx=18.5)
# ══════════════════════════════════════════════════════════════════════════
rbox(18.5, TOP_Y, 3.0, BOX_H, '#e8daef', ec='#7d3c98', lw=2.5)
txt(18.5, 9.75, 'Top-k Results', fs=15, fw='bold', color='#4a235a')
txt(18.5, 9.25, '(similar verdicts)', fs=9.5, color='#7d3c98', style='italic')

result_data = [('#1', '8.9', '#d35400'), ('#2', '7.3', '#7d3c98'), ('#3', '6.8', '#1a5276')]
for i, (rank, score, rc) in enumerate(result_data):
    ry = 8.65 - i * 0.55
    rbox(18.5, ry, 2.55, 0.44, '#f4ecf7', ec=rc, lw=1.3, radius=0.07, zorder=4)
    txt(17.35, ry, rank, fs=10.5, fw='bold', color=rc, z=5)
    txt(18.6, ry, f'Score = {score}', fs=10.5, color='#4a235a', z=5)

# ══════════════════════════════════════════════════════════════════════════
# BOTTOM LEGEND
# ══════════════════════════════════════════════════════════════════════════
rbox(10, LEG_Y, 18.8, 2.6, '#eaf2ff', ec='#2980b9', lw=2, radius=0.3)
txt(10, LEG_Y+0.95, 'Design Logic Summary', fs=13, fw='bold', color='#1a3a5c')

# DAG row
rbox(1.9, LEG_Y+0.45, 1.1, 0.45, '#fadbd8', ec='#c0392b', lw=1.5, radius=0.08)
txt(1.9, LEG_Y+0.45, 'DAG', fs=10, fw='bold', color='#922b21')
txt(10.5, LEG_Y+0.45,
    'PARENT_OF  =  Navigation structure  ->  decides  WHERE  to look for candidates',
    fs=11, color='#922b21', ha='center')

# Score row
rbox(1.9, LEG_Y-0.12, 1.1, 0.45, '#fef9e7', ec='#d4ac0d', lw=1.5, radius=0.08)
txt(1.9, LEG_Y-0.12, 'Score', fs=10, fw='bold', color='#7d6608')
txt(10.5, LEG_Y-0.12,
    'Score        =  Ranking tool          ->  decides  WHO   ranks first after retrieval',
    fs=11, color='#7d6608', ha='center')

# note
txt(10, LEG_Y-0.72,
    'Score high/low  !=  parent-child order.   '
    'Parent is determined by Fact severity priority (alpha), NOT by total score.',
    fs=10, color='#555', style='italic')

plt.tight_layout(pad=0.2)
plt.savefig('/home/aru/AI_LAW/phase3_query.png', dpi=160, bbox_inches='tight',
            facecolor='#f5f7fa')
print("Done -> /home/aru/AI_LAW/phase3_query.png")
