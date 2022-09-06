from flask import Flask, render_template, redirect, url_for, request, flash, copy_current_request_context, send_file
from dotenv import load_dotenv
from threading import Thread
import shutil
import requests
import os

load_dotenv()
END_POINT = 'http://20.125.131.148:8080/upload_bulk'

flash_list = []
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'jfif'])
string_to_replace = {'.' + i: '.png' for i in ALLOWED_EXTENSIONS}


def create_app():
    app = Flask(__name__)
    app.secret_key = 'abc'

    @app.context_processor
    def allowed_extensions():
        return {"allowed_extensions": ALLOWED_EXTENSIONS}

    @app.route('/', methods=['GET', 'POST'])
    def index():  # put application's code here
        @copy_current_request_context
        def worker():
            '''
            worker function to process files in parallel
            :return: list of files endpoints of processed images'''
            for file in os.listdir('Uploaded_files'):
                payload = {'file': open('Uploaded_files/' + file, 'rb')}
                response = requests.post(END_POINT, files=payload)
                print(response.text)
                if response.status_code != 200:
                    flash_list.append(f'Some error has occurred on {file} - <response code - {response.status_code}')
                else:
                    flash_list.append(f'processing {file} - <response code - {200}>')
                    response = requests.get(response.json()['image'])
                    png_filename = file
                    for string, replace_value in string_to_replace.items():
                        png_filename = png_filename.replace(string, replace_value)
                    with open('result/' + 'processed_' + png_filename, 'wb') as f:
                        f.write(response.content)

        if request.method == 'POST':
            '''deleting files from the api'''
            # requests.post('http://20.125.131.148:8080/deleteall').raise_for_status()
            for file in request.files.getlist('file'):
                file.save('Uploaded_files/' + file.filename)
                if file.filename.endswith(('.zip', '.rar')):
                    if file.filename.endswith('.rar'):
                        shutil.unpack_archive('Uploaded_files/' + file.filename, 'Uploaded_files', 'rar')
                    else:
                        shutil.unpack_archive('Uploaded_files/' + file.filename, 'Uploaded_files')
                    dir_name = file.filename.replace('.zip', '').replace('.rar', '')
                    for nested_file in os.listdir('Uploaded_files/' + dir_name):
                        shutil.move(f'Uploaded_files/{dir_name}/{nested_file}', 'Uploaded_files')
                    os.remove('Uploaded_files/' + file.filename)
                    os.rmdir(f'Uploaded_files/{dir_name}')
            global t
            t = Thread(target=worker)
            t.start()
            return redirect(url_for('processing'))

        response = requests.get(request.host_url + '/flush')
        print(response.text)
        return render_template('index.html')

    @app.route('/processing')
    def processing():
        return render_template('processing.html', images=[file for file in os.listdir('result')],
                               size=len(os.listdir('Uploaded_files')))

    @app.route('/get_image/<filename>')
    def get_image(filename):
        return send_file('result/' + filename, mimetype='image/png')

    @app.route("/shutdown", methods=['GET'])
    def shutdown():
        shutdown_func = request.environ.get('werkzeug.server.shutdown')
        if shutdown_func is None:
            raise RuntimeError('Not running werkzeug')
        shutdown_func()
        return "Shutting down..."

    @app.route('/flush')
    def flush_data():
        for file in os.listdir('Uploaded_files'):
            os.remove('Uploaded_files/' + file)
        for file in os.listdir('result'):
            os.remove('result/' + file)
        response = requests.post('http://20.125.131.148:8080/deleteall')
        return response.text

    @app.route('/download')
    def download():
        shutil.make_archive('result', 'zip', 'result')
        return send_file('result.zip', mimetype='application/zip')

    def get_count():
        count = len(os.listdir('result'))
        return count

    app.jinja_env.globals.update(get_count=get_count)
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(threaded=True)
