from flask import Flask, render_template, request, session, redirect, url_for, send_from_directory
from tinydb import TinyDB
from threading import Lock
import uuid
import random
import os
import csv
import io
from flask import Response

app = Flask(__name__)
app.secret_key = 'trellis_study_secret'

db = TinyDB('database.json')
responses_table = db.table('responses')
db_lock = Lock()

OBJECTS = {
    '3december_2021_-_cottage_snowglobe': {'label': 'a cottage snow globe',    'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'acoustic_guitar':                    {'label': 'an acoustic guitar',      'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'airplane_crj-900_cityjet_1':         {'label': 'a commercial airplane',   'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'antique_globe_2':                    {'label': 'an antique globe',        'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'avocado':                            {'label': 'an avocado',              'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'baloons_anil':                       {'label': 'balloons',                'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'banana':                             {'label': 'a banana',                'iterations': ['round2','round3','round4','round5','round6']},
    'birthday_cake':                      {'label': 'a birthday cake',         'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'cactus':                             {'label': 'a cactus',                'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'hamburger':                          {'label': 'a hamburger',             'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'hot_air_baloon':                     {'label': 'a hot air balloon',       'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'penguin_plush':                      {'label': 'a penguin plush toy',     'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'skateboard':                         {'label': 'a skateboard',            'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'slice_of_pizza':                     {'label': 'a slice of pizza',        'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'trophy':                             {'label': 'a trophy',                'iterations': ['round2','round3','round4','round5','round6','round7','round8']},
    'door_key':                           {'label': 'a door key',              'iterations': ['round2','round3','round4','round5','round6','round7']},
    'knife_94db219c':                     {'label': 'a knife',                 'iterations': ['round2','round3','round4','round5','round6']},
    'water_bottle':                       {'label': 'a water bottle',          'iterations': ['round2','round3','round4','round5','round6','round7']},
}

OBJECT_KEYS = list(OBJECTS.keys())

@app.route('/videos/<path:filename>')
def serve_video(filename):
    videos_dir = os.path.join(app.root_path, 'static', 'videos')
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
    return redirect(url_for('study'))

@app.route('/study', methods=['GET', 'POST'])
def study():
    if 'participant_id' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        choice = request.form.get('choice')
        obj = OBJECT_KEYS[session['object_index']]
        phase = session['phase']

        if phase == 'pick_best':
            # Store their chosen iteration and set up shuffled A/B for phase 2
            session['best_iteration'] = choice
            if random.random() > 0.5:
                session['video_A'] = 'round1'
                session['video_B'] = choice
            else:
                session['video_A'] = choice
                session['video_B'] = 'round1'
            session['phase'] = 'vs_baseline'

            with db_lock:
                responses_table.insert({
                    'participant_id': session['participant_id'],
                    'age': session.get('age', 'not provided'),
                    'object': obj,
                    'phase': 'pick_best',
                    'choice': choice
                })
            return redirect(url_for('study'))

        else:
            # choice is 'A' or 'B', log what they actually picked
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

            session['object_index'] += 1
            session['phase'] = 'pick_best'
            if session['object_index'] >= len(OBJECT_KEYS):
                return redirect(url_for('done'))
            return redirect(url_for('study'))

    obj = OBJECT_KEYS[session['object_index']]
    phase = session['phase']
    label = OBJECTS[obj]['label']
    current = session['object_index'] + 1
    total = len(OBJECT_KEYS)

    if phase == 'pick_best':
        return render_template('pick_best.html',
                               obj=obj,
                               label=label,
                               iterations=OBJECTS[obj]['iterations'],
                               current=current,
                               total=total)
    else:
        return render_template('vs_baseline.html',
                               obj=obj,
                               label=label,
                               video_A=session['video_A'],
                               video_B=session['video_B'],
                               current=current,
                               total=total)

@app.route('/done')
def done():
    return render_template('done.html')

@app.route('/admin/download')
def download_data():
    all_responses = responses_table.all()
    if not all_responses:
        return "No data yet.", 200

    output = io.StringIO()
    fieldnames = ['participant_id', 'age', 'object', 'phase', 'choice', 'video_A', 'video_B', 'chose_round']
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(all_responses)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=study_results.csv'}
    )

@app.route('/admin')
def admin_dashboard():
    all_responses = responses_table.all()
    
    # Count unique participants who completed the study
    completed = {}
    for r in all_responses:
        pid = r['participant_id']
        if pid not in completed:
            completed[pid] = set()
        completed[pid].add(r['object'])
    
    total_participants = len(completed)
    total_objects = len(OBJECTS)
    
    # Per object stats
    object_stats = {}
    for obj in OBJECTS:
        object_stats[obj] = {
            'label': OBJECTS[obj]['label'],
            'responses': 0,
            'refined_wins': 0,
            'baseline_wins': 0,
        }
    
    for r in all_responses:
        if r['phase'] == 'vs_baseline' and r['object'] in object_stats:
            object_stats[r['object']]['responses'] += 1
            if r.get('chose_round', 'round1') != 'round1':
                object_stats[r['object']]['refined_wins'] += 1
            else:
                object_stats[r['object']]['baseline_wins'] += 1
    
    # Overall win rate
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
            body {{ font-family: Arial, sans-serif; max-width: 1000px; margin: 40px auto; background: #f9f9f9; padding: 0 20px; }}
            h1 {{ color: #2c3e50; }}
            .stats {{ display: flex; gap: 20px; margin: 30px 0; flex-wrap: wrap; }}
            .stat-card {{ background: white; border-radius: 10px; padding: 20px 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }}
            .stat-card h2 {{ font-size: 2.5em; color: #2c3e50; margin: 0; }}
            .stat-card p {{ color: #888; margin: 5px 0 0; }}
            table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            th {{ background: #2c3e50; color: white; padding: 12px 16px; text-align: left; }}
            td {{ padding: 10px 16px; border-bottom: 1px solid #eee; }}
            tr:last-child td {{ border-bottom: none; }}
            .win {{ color: green; font-weight: bold; }}
            .lose {{ color: #e74c3c; font-weight: bold; }}
            .bar-bg {{ background: #eee; border-radius: 4px; height: 10px; width: 150px; display: inline-block; vertical-align: middle; }}
            .bar-fill {{ background: #2c3e50; border-radius: 4px; height: 10px; }}
            .refresh {{ color: #888; font-size: 0.85em; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <h1>TRELLIS Study Dashboard</h1>
        <p class="refresh">Auto-refreshes every 30 seconds</p>
        
        <div class="stats">
            <div class="stat-card">
                <h2>{total_participants}</h2>
                <p>Participants</p>
            </div>
            <div class="stat-card">
                <h2>{total_comparisons}</h2>
                <p>Total Comparisons</p>
            </div>
            <div class="stat-card">
                <h2>{overall_win_rate}%</h2>
                <p>Refined Model Win Rate</p>
            </div>
        </div>

        <table>
            <tr>
                <th>Object</th>
                <th>Responses</th>
                <th>Refined Wins</th>
                <th>Baseline Wins</th>
                <th>Win Rate</th>
            </tr>
    """

    for obj, stats in object_stats.items():
        win_rate = round(stats['refined_wins'] / stats['responses'] * 100, 1) if stats['responses'] > 0 else 0
        bar_width = int(win_rate * 1.5)
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
            </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """
    return html
if __name__ == '__main__':
    app.run(debug=True)