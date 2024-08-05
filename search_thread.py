import hashlib, os

from PySide6.QtCore import QThread, Signal


def md5_for_file(fname, block_size=2**20):
    f = open(fname, 'rb')
    md5 = hashlib.md5()
    while True:
        data = f.read(block_size)
        if not data:
            break
        md5.update(data)
    f.close()
    return md5.digest()


class DuplicatesSearchThread(QThread):

    progress_update = Signal(int)
    search_aborted = Signal()
    done = Signal(object)


    def __init__(self, dir, done_callback):
        super().__init__()

        self.dir = dir
        self.done.connect(done_callback)
        self.should_abort = False


    def run(self):
        sizes = {}
        for root, dirs, files in os.walk(self.dir):
            for fname in files:
                if self.should_abort:
                    self.search_aborted.emit()
                    return

                fullname = os.path.abspath(os.path.join(root, fname))
                file_size = os.path.getsize(fullname)
                if file_size not in sizes:
                    sizes[file_size] = [fullname]
                else:
                    sizes[file_size].append(fullname)

        sizes = { k: v for k, v in sizes.items() if len(v) > 1 }
        hashes = {}
        total_files_to_check = sum([len(v) for v in sizes.values()])
        cur_file = 0

        for same_size_files in sizes.values():
            for fname in same_size_files:
                if self.should_abort:
                    self.search_aborted.emit()
                    return

                file_hash = md5_for_file(fname)
                if file_hash not in hashes:
                    hashes[file_hash] = [fname]
                else:
                    hashes[file_hash].append(fname)

                cur_file += 1
                percent = int((cur_file / total_files_to_check) * 100)
                self.progress_update.emit(percent)

        dups = { k: v for k, v in hashes.items() if len(v) > 1 }
        self.done.emit(dups)

