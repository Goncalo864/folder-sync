import hashlib
import logging
import os
import shutil
import schedule
import time
import re
from shutil import copystat, Error, copy2
 
# Records the object in the log file
def log_object(object, operation):
    if operation == 'delete':
        print(f"DELETED -> Object '{os.path.basename(object)}'  at {object}")
        logging.warning(f"DELETED -> Object '{os.path.basename(object)}'  at {object}")
    elif operation == 'update':
        print(f"UPDATED -> Object '{os.path.basename(object)}'  at {object}")
        logging.warning(f"UPDATED -> Object '{os.path.basename(object)}'  at {object}")
    elif operation == 'create':
        print(f"CREATED -> Object '{os.path.basename(object)}'  at {object}")
        logging.warning(f"CREATED -> Object '{os.path.basename(object)}'  at {object}")
    elif operation == 'error':
        print(f"ERROR -> {object}")
        logging.critical(f"ERROR -> {object}")


def remove_item(object):
    if os.path.isdir(object):
        shutil.rmtree(object)
        log_object(object, 'delete')
    elif os.path.isfile(object):
        os.remove(object)
        log_object(object, 'delete')

# Deletes all the folder that don't match
def check_sync(folder1, folder2, dstname):
    if folder1 != folder2:
        difference = [x for x in folder2 if x not in folder1]

        for different_folder in difference:
            different_folder = os.path.join(dstname, different_folder)
            remove_item(different_folder)


def check_hash(file_path):
    with open(file_path, 'rb') as file:
        file_contents = file.read()

        md5_hash = hashlib.md5(file_contents).hexdigest()

    return md5_hash


def _copytree(entries, src, dst, empty):
    os.makedirs(dst, exist_ok=True)
    errors = []
    copy_function = copy2
    # For each entry  will catch the object to be copied, its destination path, and its original path.
    for srcentry in entries:
        srcname = os.path.join(src, srcentry.name)
        dstname = os.path.join(dst, srcentry.name)
        srcobj = srcentry if copy_function else srcname
        try:
            if srcentry.is_dir():

                if os.path.exists(dstname):
                    folder1 = os.listdir(srcobj.path)
                    folder2 = os.listdir(dstname)

                    if folder1 and not folder2:
                        copytree(srcobj, dstname)
                        log_object(srcobj.path, 'create')
                    check_sync(folder1, folder2, dstname)
                    copytree(srcobj.path, dstname)
                else:
                    copytree(srcobj, dstname)
                    log_object(srcobj.path, 'create')
            else:
                file_exists = os.path.exists(dstname)
                sync = False

                if file_exists:
                    sync = check_hash(srcobj.path) == check_hash(dstname)
                if not file_exists:
                    copy_function(srcobj, dstname)

                    log_object(srcobj, 'create')
                elif file_exists and not sync:
                    remove_item(dstname)

                    with open(log_path, 'r+') as fp:
                        lines = fp.readlines()
                        fp.seek(0)
                        fp.truncate()
                        fp.writelines(lines[:-1])

                    copy_function(srcobj, dstname)
                    log_object(srcobj.path, 'update')
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Error as err:
            errors.extend(err.args[0])
        except OSError as why:
            errors.append((srcname, dstname, str(why)))
    try:
        copystat(src, dst)
    except OSError as why:
        # Copying file access times may fail on Windows
        if getattr(why, 'winerror', None) is None:
            errors.append((src, dst, str(why)))
            log_object(str(why), 'error')
    if errors:
        raise Error(errors)
    return dst


def copytree(src, dst):
    with os.scandir(src) as itr:
        entries = list(itr)
        empty = False
        if not entries:
            empty = True
    return _copytree(entries=entries, src=src, dst=dst, empty=empty)


while True:
    src = os.path.abspath(input('Enter the folder name you want to copy:\n'))
    dst = os.path.abspath(input('Enter the folder name where you want to save the copy:\n'))
    log_path = os.path.abspath(input('Enter the file name where you want to save logs (make sure to include the file extension):\n'))
    schedule_time = str(input('Specify the synchronization interval(E.G. "10:30")(the script will run everyday): \n'))
    if not os.path.exists(src):
        print("Folder not found at ", src)
    elif not os.path.exists(dst):
        print("Folder not found at ", dst)
    elif not os.path.exists(log_path):
        print("File not found at ", log_path)
    elif not re.match('^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$', schedule_time):
        print("Enter a valid interval")
    else:
        logging.basicConfig(filename=log_path, format='%(asctime)s: %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')
        break


def sync_folder():
    folder1 = os.listdir(src)
    folder2 = os.listdir(dst)
    check_sync(folder1, folder2, dst)

    copytree(src, dst)


sync_folder()

schedule.every().day.at(schedule_time).do(sync_folder)
while True:
    schedule.run_pending()
    time.sleep(1)


