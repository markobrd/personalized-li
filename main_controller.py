from multiprocessing import Process, Queue, current_process
import time
from flask_server import make_server, PORT
import webbrowser
from scrape_linkedin import main as run_scraper
import asyncio


def start_flask(queue: Queue):
    app = make_server(queue)
    webbrowser.open_new_tab("http://127.0.0.1:5000")
    app.run(port=PORT, debug=False)


def start_search(q):
    asyncio.run(run_scraper(q))


def main():
    q = Queue()
    p1 = Process(target=start_flask, args=(q,), name="Main server")
    p1.start()
    p2 = None
    try:
        while True:
            time.sleep(1)
            if not q.empty():
                if True is False and (p2 is None or not p2.is_alive()):
                    p2 = Process(target=start_search, args=(q,), name="Search")
                    p2.start()
    except:
        p1.join()
        if p2:
            p2.join()
    return


if __name__ == "__main__":
    main()
