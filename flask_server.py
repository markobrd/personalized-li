from flask import Flask, jsonify, send_from_directory, request, render_template
import os
import json
import webbrowser
import yaml
from multiprocessing import Queue
from scrape_linkedin import process_posts
from datetime import datetime

with open('config.yaml') as config_file:
    config = yaml.safe_load(config_file)

DATA_FOLDER = "JSON_DATA"
PROCESSED_DATA_FOLDER = "PROCESSED_POSTS\\mark"
NUM_POSTS_PER_LOAD = config['posts_to_load']
PORT = config['PORT']
files = sorted(os.listdir(DATA_FOLDER))
# REMOVE LATER - REPLACE WITH LOCAL REQUEST ISSUER PEOPLE_OF_INTEREST
PEOPLE_OF_INTEREST = config['stalklist']
TOPICS = config['topics']


def check_recomendations_exist(user="mark", prompt=str(TOPICS)):
    if os.path.exists(os.path.join('PROCESSED_POSTS', user, f'{prompt}.json')):
        return True

    if not os.path.exists(os.path.join('PROCESSED_POSTS', user)):
        os.mkdir(os.path.join('PROCESSED_POSTS', user))
        print("User directory created")

    return False


def find_people_by_id(id, user, return_prompt=0):
    with open(os.path.join("USER_REQUESTS", "requests.json"), "r") as file:
        data = json.load(file)

        print(user)
        print(id)
        counter = 0
        for line in data:
            if line['user'] == user:
                if counter == id:
                    if(not return_prompt):
                        return line['task']['people']
                    else:
                        return line['task']['prompt']
                else:
                    counter += 1
    raise Exception("Invalid index sent")


async def process_user_posts(id, user="mark", prompt=str(TOPICS)):
    with open(f'PROCESSED_POSTS/{user}/{prompt}.json', "w+") as file1:
        data = []
        for person in find_people_by_id(id, user):
            main_path = DATA_FOLDER + '/' + person
            person_files = sorted(os.listdir(main_path))

            for person_file in person_files:
                file_path = os.path.join(main_path, person_file)
                if not file_path.endswith(".json"):
                    continue
                print("Processing" + file_path + "\n\n\n\n")

                with open(file_path, "r") as f:
                    data += await process_posts(json.load(f), prompt)
                #     print(json.load(f))
                #     print("\n\n\n\n")

        json.dump(data, file1, indent=4)


def find_missing_people(people):
    missing_people: list[str] = []
    for person in people:
        main_path = os.path.join(DATA_FOLDER, person)
        if not os.path.exists(main_path):
            missing_people.append(person)
            continue

        files = sorted(os.listdir((main_path)))
        if len(files) == 0:
            missing_people.append(person)
            continue
        i = 0
        while i < len(files) and not files[i].endswith(".json"):
            i += 1

        if i >= len(files):
            missing_people.append(person)
            continue

        date = files[-1][(len(person) + len("_posts_")):-5]
        print(date)
        # if (datetime.now() - datetime.strptime(date, '%Y-%m-%d')).total_seconds()//(3600*24) >= 1:
        # missing_people.append(person)
    return missing_people


def create_request_file(user, people, prompt, ready):
    path = os.path.join("USER_REQUESTS")

    if not os.path.exists(path):
        os.mkdir(path)

    filename = "requests.json"
    path = os.path.join(path, filename)
    with open(path, "r") as file:
        data = json.load(file)
        data.append({'ready': ready, 'task': {
                    'people': people, 'prompt': prompt}, 'user': user})
    with open(path, "w") as file:
        json.dump(data, file, indent=4)


def check_ready(people):
    missing_people = find_missing_people(people)
    if len(missing_people) == 0:
        return True
    else:
        return False


def make_server(queue: Queue):
    app = Flask(__name__)

    @ app.route('/')
    def home():
        return render_template("./give_task.html")
        return send_from_directory('filltered_li.html')
        # return jsonify({})

    @app.route('/task')
    def task():
        user = request.args.get("user")
        id = request.args.get("id")

        return render_template('filltered_li.html', message={"user": str(user), "id": id})

    @ app.route('/submit_request', methods=['POST'])
    async def submit_request():
        user = request.json.get("user")

        people = request.json.get("people")
        for person in people:
            print(person)
        missing_people = find_missing_people(people)

        prompt = request.json.get("prompt")

        if len(missing_people) == 0:

            create_request_file(user, people, prompt, True)
            return jsonify({'ready': True, 'task': {'people': people, 'prompt': prompt}})

        for person in missing_people:
            queue.put(person)

        create_request_file(user, people, prompt, False)
        return jsonify({'ready': False, 'task': {'people': people, 'prompt': prompt}})

    @ app.route('/get_requests', methods=['POST'])
    async def get_requests():
        user = request.json.get("user")
        path = os.path.join("USER_REQUESTS", "requests.json")
        print(path)
        if(not os.path.exists(path)):
            return jsonify([])

        requests = []
        with open(path, "r+") as file:
            data = json.load(file)
            for line in data:
                if line['user'] != user:
                    continue

                if not line['ready']:
                    line['ready'] = check_ready(line['task']['people'])

                requests.append(line)
        with open(path, "w") as file:
            json.dump(data, file, indent=4)
        return jsonify(requests)

    @ app.route('/load_data', methods=['POST'])
    async def load_data():
        user = request.json.get("user")
        id = int(request.json.get("id"))
        prompt = find_people_by_id(id, user, 1)
        if not check_recomendations_exist(user, prompt=prompt):
            await process_user_posts(id, user=user, prompt=prompt)

        print("rec checked")
        file_index = int(request.json.get('file_index', -1))
        elem_index = int(request.json.get('elem_index', 0))

        processed_data_folder = os.path.join("PROCESSED_POSTS", user)
        files = sorted(os.listdir(processed_data_folder))  # REPLACE LATER!!!

        posts_left_to_load = NUM_POSTS_PER_LOAD
        out = []
        while file_index < len(files) and file_index != -1:
            file_path = os.path.join(
                processed_data_folder, files[-file_index-1])
            if not file_path.endswith(".json"):
                file_index += 1
                continue

            with open(file_path) as f:
                data = json.load(f)

            if elem_index + posts_left_to_load <= len(data):
                out += data[elem_index:elem_index+posts_left_to_load]
                elem_index += posts_left_to_load
            else:
                out += data[elem_index:]
                if file_index + 1 < len(files):
                    posts_left_to_load -= len(data[elem_index:])
                    elem_index = 0
                    file_index += 1
                    continue
                else:
                    file_index = -1

            return jsonify({'data': out, 'next': file_index, 'elem_index': elem_index})

        return jsonify({'data': [], 'next': -1, 'elem_index': -1})
    return app


if __name__ == '__main__':
    webbrowser.open_new_tab("http://127.0.0.1:5000")
    app = make_server(Queue())
    app.run(port=PORT, debug=False)
