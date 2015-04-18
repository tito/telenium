from bottle import static_file, Bottle, run
from os.path import dirname, join


app = Bottle()


@app.route("/<filepath:path>")
def server_static(filepath):
    print filepath
    return static_file(filepath, root=join(dirname(__file__), "static"))


if __name__ == "__main__":
    run(app, host="localhost", port=8080, debug=True)
