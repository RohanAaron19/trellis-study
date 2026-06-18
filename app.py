from flask import Flask, render_template, request, session, redirect, url_for, send_from_directory
from tinydb import TinyDB
from threading import Lock
import uuid
import random
import os
import csv
import io
import json
from flask import Response
from scipy.stats import binomtest

app = Flask(__name__)
app.secret_key = 'trellis_study_secret'

db = TinyDB('/data/database.json')
responses_table = db.table('responses')
db_lock = Lock()

# ============================================================================
# OBJECTS — fill this in with the models for this round of the study.
#
# Format:
#   'folder_name': {
#       'label': 'human readable label shown to participants',
#       'iterations': ['round2', 'round3', ...]   # refined iterations to choose from
#                                                    # (round1 is always the baseline)
#   }
#
# Each entry assumes videos live at:
#   static/<folder_name>/round1.mp4   <- baseline
#   static/<folder_name>/round2.mp4   <- refined iteration 2
#   static/<folder_name>/round3.mp4   <- refined iteration 3
#   ... etc, matching whatever is listed in 'iterations'
# ============================================================================
OBJECTS = {
    'airplane_002':   {'label': 'an airplane',        'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'apple_002':      {'label': 'an apple',           'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'ball_001':       {'label': 'a ball',             'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'ball_002':       {'label': 'a ball',             'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'banana_001':     {'label': 'a banana',           'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'bicycle_001':    {'label': 'a bicycle',          'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'boat_002':       {'label': 'a boat',             'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'bottle_001':     {'label': 'a bottle',           'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'bread_001':      {'label': 'bread',              'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'bread_002':      {'label': 'bread',              'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'bunny_001':      {'label': 'a bunny',            'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'bus_001':        {'label': 'a bus',              'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'butterfly_001':  {'label': 'a butterfly',        'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'cake_001':       {'label': 'a cake',             'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'candy_000':      {'label': 'candy',              'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'candy_002':      {'label': 'candy',              'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'cat_000':        {'label': 'a cat',              'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'chair_001':      {'label': 'a chair',            'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'chess_piece_000':{'label': 'a chess piece',      'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'chicken_000':    {'label': 'a chicken',          'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'cookie_000':     {'label': 'a cookie',           'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'crab_001':       {'label': 'a crab',             'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'cow_001':        {'label': 'a cow',              'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'cupcake_001':    {'label': 'a cupcake',          'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'dinosaur_001':   {'label': 'a dinosaur',         'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'dog_001':        {'label': 'a dog',              'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'donut_002':      {'label': 'a donut',            'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'elephant_001':   {'label': 'an elephant',        'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'fish_000':       {'label': 'a fish',             'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'flower_000':     {'label': 'a flower',           'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'fries_000':      {'label': 'fries',              'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'frog_000':       {'label': 'a frog',             'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'giraffe_001':    {'label': 'a giraffe',          'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'grapes_000':     {'label': 'grapes',             'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'glass_001':      {'label': 'a glass',            'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'guitar_000':     {'label': 'a guitar',           'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'hamburger_000':  {'label': 'a hamburger',        'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'hat_001':        {'label': 'a hat',              'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'helicopter_000': {'label': 'a helicopter',       'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'horse_000':      {'label': 'a horse',            'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'ice_cream_001':  {'label': 'ice cream',          'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'keyboard_000':   {'label': 'a keyboard',         'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'knife_001':      {'label': 'a knife',            'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'ladder_000':     {'label': 'a ladder',           'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'laptop_001':     {'label': 'a laptop',           'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'light_bulb_001': {'label': 'a light bulb',       'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'mouse_000':      {'label': 'a mouse',            'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'marker_002':     {'label': 'a marker',           'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'motorcycle_001': {'label': 'a motorcycle',       'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'mug_001':        {'label': 'a mug',              'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'octopus_001':    {'label': 'an octopus',         'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'orange_001':     {'label': 'an orange',          'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'pear_001':       {'label': 'a pear',             'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'pencil_011':     {'label': 'a pencil',           'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'penguin_001':    {'label': 'a penguin',          'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'truck_001':      {'label': 'a truck',            'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'whale_000':      {'label': 'a whale',            'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
}

OBJECT_KEYS = list(OBJECTS.keys())
OBJECTS_PER_PARTICIPANT = 20

# 7-point rating scale shown on the final page for each object
RATING_LABELS = [
    "Doesn't look like anything — no recognizable form",
    "Looks like the wrong thing — clear form, wrong identity",
    "Goes in the right direction — vague hints of the correct object",
    "Recognizable knowing what it's supposed to be — identifiable only with knowing it",
    "Somewhat looks like the target object — identifiable on its own, but loosely",
    "Clearly recognizable as the target — confidently the right object, but with minor issues",
    "Very convincing — no visual issues",
]


@app.route('/videos/<path:filename>')
def serve_video(filename):
    videos_dir = os.path.join(app.root_path, 'static')
    return send_from_directory(videos_dir, filename)


@app.route('/')
def index():
    session['participant_id'] = str(uuid.uuid4())
    session['object_index'] = 0
    session['phase'] = 'pick_best'
    return render_template('index.html')


@app.route('/start')
def start():
    session['object_index'] = 0
    session['phase'] = 'pick_best'
    session['age'] = request.args.get('birth_year', 'not provided')
    # Each participant sees a random subset of OBJECTS_PER_PARTICIPANT objects,
    # not the full OBJECT_KEYS list, so the study stays short per-person while
    # still covering all objects across many participants.
    pool = OBJECT_KEYS.copy()
    random.shuffle(pool)
    order = pool[:OBJECTS_PER_PARTICIPANT]
    session['object_order'] = order
    return redirect(url_for('study'))


@app.route('/study', methods=['GET', 'POST'])
def study():
    if 'participant_id' not in session:
        return redirect(url_for('index'))

    order = session.get('object_order', OBJECT_KEYS)

    if request.method == 'POST':
        obj = order[session['object_index']]
        phase = session['phase']

        if phase == 'pick_best':
            # Page 1: participant picked their favorite iteration among all refined rounds
            choice = request.form.get('choice')
            session['best_iteration'] = choice

            with db_lock:
                responses_table.insert({
                    'participant_id': session['participant_id'],
                    'age': session.get('age', 'not provided'),
                    'object': obj,
                    'phase': 'pick_best',
                    'choice': choice
                })

            session['phase'] = 'vs_baseline'
            return redirect(url_for('study'))

        elif phase == 'vs_baseline':
            # Page 2: best refined iteration vs baseline, A/B randomized
            choice = request.form.get('choice')

            with db_lock:
                responses_table.insert({
                    'participant_id': session['participant_id'],
                    'object': obj,
                    'phase': 'vs_baseline',
                    'video_A': session['video_A'],
                    'video_B': session['video_B'],
                    'choice': choice,
                    'chose_round': session['video_A'] if choice == 'A' else session['video_B']
                })

            session['phase'] = 'rate'
            return redirect(url_for('study'))

        else:
            # Page 3: 7-point rating scale on the winning video from page 2
            rating = request.form.get('rating')

            with db_lock:
                responses_table.insert({
                    'participant_id': session['participant_id'],
                    'object': obj,
                    'phase': 'rate',
                    'rated_video': session.get('winner_video', 'unknown'),
                    'rating': rating
                })

            session['object_index'] += 1
            session['phase'] = 'pick_best'

            if session['object_index'] >= len(order):
                return redirect(url_for('done'))

            return redirect(url_for('study'))

    # ---- GET: render the current phase ----
    obj = order[session['object_index']]
    phase = session['phase']
    label = OBJECTS[obj]['label']
    current = session['object_index'] + 1
    total = len(order)

    if phase == 'pick_best':
        return render_template(
            'pick_best.html',
            obj=obj,
            label=label,
            iterations=OBJECTS[obj]['iterations'],
            current=current,
            total=total
        )

    elif phase == 'vs_baseline':
        best_choice = session.get('best_iteration')
        if random.random() > 0.5:
            session['video_A'] = 'round1'
            session['video_B'] = best_choice
        else:
            session['video_A'] = best_choice
            session['video_B'] = 'round1'

        return render_template(
            'vs_baseline.html',
            obj=obj,
            label=label,
            video_A=session['video_A'],
            video_B=session['video_B'],
            current=current,
            total=total
        )

    else:  # rate
        # Determine which video "won" page 2 to show on the rating page
        last_response = responses_table.search(
            lambda r: r.get('participant_id') == session['participant_id']
            and r.get('object') == obj
            and r.get('phase') == 'vs_baseline'
        )
        winner_video = last_response[-1]['chose_round'] if last_response else 'round1'
        session['winner_video'] = winner_video

        return render_template(
            'rate.html',
            obj=obj,
            label=label,
            video=winner_video,
            rating_labels=RATING_LABELS,
            current=current,
            total=total
        )


@app.route('/done')
def done():
    return render_template('done.html')


@app.route('/admin/download')
def download_data():
    all_responses = responses_table.all()
    if not all_responses:
        return "No data yet.", 200

    output = io.StringIO()
    fieldnames = ['participant_id', 'age', 'object', 'phase', 'choice',
                  'video_A', 'video_B', 'chose_round', 'rated_video', 'rating']
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(all_responses)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=study_results.csv'}
    )


@app.route('/admin/db')
def view_db():
    all_responses = responses_table.all()
    return f"<pre>{json.dumps(all_responses, indent=2)}</pre>"

@app.route('/admin/reset')
   def reset_data():
       with db_lock:
           responses_table.truncate()
       return "Database cleared.", 200


@app.route('/admin')
def admin_dashboard():
    all_responses = responses_table.all()

    completed = {}
    for r in all_responses:
        pid = r['participant_id']
        completed.setdefault(pid, set()).add(r['object'])

    total_participants = len(completed)

    object_stats = {}
    for obj in OBJECTS:
        object_stats[obj] = {
            'label': OBJECTS[obj]['label'],
            'responses': 0,
            'refined_wins': 0,
            'baseline_wins': 0,
            'avg_rating': None,
            'rating_count': 0,
            'rating_sum': 0,
        }

    for r in all_responses:
        if r.get('object') not in object_stats:
            continue

        if r['phase'] == 'vs_baseline':
            chose = r.get('chose_round', 'round1')
            if not str(chose).startswith('round'):
                continue
            object_stats[r['object']]['responses'] += 1
            if chose != 'round1':
                object_stats[r['object']]['refined_wins'] += 1
            else:
                object_stats[r['object']]['baseline_wins'] += 1

        elif r['phase'] == 'rate':
            try:
                rating_val = float(r.get('rating'))
                object_stats[r['object']]['rating_sum'] += rating_val
                object_stats[r['object']]['rating_count'] += 1
            except (TypeError, ValueError):
                pass

    for obj, stats in object_stats.items():
        if stats['rating_count'] > 0:
            stats['avg_rating'] = round(stats['rating_sum'] / stats['rating_count'], 2)

    total_comparisons = sum(o['responses'] for o in object_stats.values())
    total_refined_wins = sum(o['refined_wins'] for o in object_stats.values())
    overall_win_rate = round((total_refined_wins / total_comparisons * 100), 1) if total_comparisons > 0 else 0

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <title>Study Admin Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 40px auto; background: #f9f9f9; padding: 0 20px; }}
        h1 {{ color: #2c3e50; }}
        .stats {{ display: flex; gap: 20px; margin: 30px 0; flex-wrap: wrap; }}
        .stat-card {{ background: white; border-radius: 10px; padding: 20px 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }}
        .stat-card h2 {{ font-size: 2.5em; color: #2c3e50; margin: 0; }}
        .stat-card p {{ color: #888; margin: 5px 0 0; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        th {{ background: #2c3e50; color: white; padding: 12px 16px; text-align: left; font-size: 0.9em; }}
        td {{ padding: 10px 16px; border-bottom: 1px solid #eee; font-size: 0.9em; }}
        tr:last-child td {{ border-bottom: none; }}
        .win {{ color: green; font-weight: bold; }}
        .lose {{ color: #e74c3c; font-weight: bold; }}
        .sig {{ color: green; font-weight: bold; }}
        .not-sig {{ color: #e74c3c; }}
        .bar-bg {{ background: #eee; border-radius: 4px; height: 10px; width: 120px; display: inline-block; vertical-align: middle; }}
        .bar-fill {{ background: #2c3e50; border-radius: 4px; height: 10px; }}
        .refresh {{ color: #888; font-size: 0.85em; margin-top: 10px; }}
    </style>
    </head>
    <body>
    <h1>TRELLIS Study Dashboard</h1>
    <p class="refresh">Auto-refreshes every 30 seconds</p>

    <div class="stats">
        <div class="stat-card"><h2>{total_participants}</h2><p>Participants</p></div>
        <div class="stat-card"><h2>{total_comparisons}</h2><p>Total Comparisons</p></div>
        <div class="stat-card"><h2>{overall_win_rate}%</h2><p>Refined Model Win Rate</p></div>
    </div>

    <table>
    <tr>
        <th>Object</th>
        <th>Responses</th>
        <th>Refined Wins</th>
        <th>Baseline Wins</th>
        <th>Win Rate</th>
        <th>p-value</th>
        <th>Significant? (p&lt;0.05)</th>
        <th>Avg Rating (1-7)</th>
    </tr>
    """

    for obj, stats in object_stats.items():
        win_rate = round(stats['refined_wins'] / stats['responses'] * 100, 1) if stats['responses'] > 0 else 0
        bar_width = int(win_rate * 1.2)

        if stats['responses'] > 0:
            result = binomtest(stats['refined_wins'], stats['responses'], p=0.5, alternative='two-sided')
            pval = result.pvalue
            pval_str = f"{pval:.4f}"
            sig_str = "<span class='sig'>✅ Yes</span>" if pval < 0.05 else "<span class='not-sig'>❌ No</span>"
        else:
            pval_str = "N/A"
            sig_str = "N/A"

        avg_rating_str = f"{stats['avg_rating']} ({stats['rating_count']})" if stats['avg_rating'] is not None else "N/A"

        html += f"""
        <tr>
            <td>{stats['label']}</td>
            <td>{stats['responses']}</td>
            <td class="win">{stats['refined_wins']}</td>
            <td class="lose">{stats['baseline_wins']}</td>
            <td>
                <div class="bar-bg"><div class="bar-fill" style="width:{bar_width}px"></div></div>
                {win_rate}%
            </td>
            <td>{pval_str}</td>
            <td>{sig_str}</td>
            <td>{avg_rating_str}</td>
        </tr>
        """

    html += """
    </table>
    </body>
    </html>
    """

    return html


@app.route('/admin/import', methods=['POST'])
def import_data():
    data = request.get_json()
    if not data or 'rows' not in data:
        return {'error': 'no data'}, 400

    with db_lock:
        for row in data['rows']:
            responses_table.insert(row)

    return {'imported': len(data['rows'])}, 200


if __name__ == '__main__':
    app.run(debug=True)
