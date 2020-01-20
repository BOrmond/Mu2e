import csv
import os


def read_cc():

    project_dir = os.path.dirname(os.path.abspath(__file__))
    upload_dir = os.path.join(project_dir, "upload1")

    files = os.listdir(upload_dir)
    set = 26
    continuity_err_pins = []
    crosstalk_err_pins = {}
    filenum = 0

    for file in files:
        with open(os.path.join(upload_dir, file)) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",")
            line_count = 0
            for row in csv_reader:
                if line_count != 0:
                    pin = filenum * set + (int(row[0]) - 2)
                    if int(row[1]) == 0:
                        if pin not in continuity_err_pins:
                            continuity_err_pins += [pin]
                    if int(row[2]) != 0 and int(row[2]) != 999:
                        in_pin = filenum * set + (int(row[2]) - set - 1)
                        out_pin = filenum * set + (int(row[3]) - 2)
                        if pin not in crosstalk_err_pins.keys():
                            crosstalk_err_pins[pin] = [out_pin]
                        elif in_pin not in crosstalk_err_pins[pin]:
                            crosstalk_err_pins[pin].append(out_pin)

                line_count += 1
        filenum += 1

    for file in files:
        os.remove(os.path.join(upload_dir, file))

    return sorted(continuity_err_pins), crosstalk_err_pins


def read_ldo(index):

    project_dir = os.path.dirname(os.path.abspath(__file__))
    upload_dir = os.path.join(project_dir, "upload2")

    files = os.listdir(upload_dir)
    voltages = ""

    for file in files:
        with open(os.path.join(upload_dir, file)) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter = ",")
            for row in csv_reader:
                if row[0] == index:
                    voltages = " ".join(row[1:7])

    for file in files:
        os.remove(os.path.join(upload_dir, file))

    return voltages

