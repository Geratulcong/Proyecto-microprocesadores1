import mariadb


def get_connection():

    return mariadb.connect(
        host="192.168.1.5",
        port=3306,
        user="raspberry",
        password="1234",
        database="detector_caidas"
    )