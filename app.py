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

if __name__ == '__main__':
    app.run(debug=True)