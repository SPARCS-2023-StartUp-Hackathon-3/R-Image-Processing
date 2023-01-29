from PIL import Image
import numpy as np
import cv2 as cv
from flask import Flask, request
import boto3, botocore
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from config import (
    AWS_ACCESS_KEY,
    AWS_SECRET_KEY,
    BUCKET_NAME,
    DB_host,
    DB_name,
    DB_user,
    DB_password,
    DB_port,
)
import os.path
import psycopg2

app = Flask(__name__)
app.config["S3_LOCATION"] = "http://{}.s3.amazonaws.com/".format(BUCKET_NAME)

# generate Postgresql connection
def DB_connection():
    try:
        db = psycopg2.connect(
            host=DB_host,
            dbname=DB_name,
            user=DB_user,
            password=DB_password,
            port=DB_port,
        )
    except Exception as e:
        print(e)
    else:
        print("postgres connected!")
        return db


# generate S3 connection
def s3_connection():
    try:
        s3 = boto3.client(
            service_name="s3",
            region_name="ap-northeast-2",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
        )
    except Exception as e:
        print(e)
    else:
        print("s3 bucket connected!")
        return s3


def prefix_exists(s3, path):
    res = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=path, MaxKeys=1)
    return "Contents" in res


def s3_put_object(s3, file, filename, contenttype):
    try:
        if prefix_exists(s3, file):
            # 이미 존재하는 file
            return False
        else:
            response = s3.put_object(
                Body=file,
                Bucket=BUCKET_NAME,
                Key=filename,
                ContentType=contenttype,
                ACL="private",
            )

    except Exception as e:
        return False
    return True


# afterprocessing is consider of combine edge and original image+transparent but now just edge
def afterprocessing(img, filter=3, iterations=1, alpha=0.5, beta=0.5, gamma=0):

    kernel = np.ones((filter, filter), np.uint8)
    src_dilation = cv.dilate(img, kernel, iterations)
    _, alpha = cv.threshold(src_dilation, 0, 255, cv.THRESH_BINARY)

    RGB = cv.cvtColor(src_dilation, cv.COLOR_GRAY2RGB)
    RGB[:, :, 0] = RGB[:, :, 0] * 46
    RGB[:, :, 1] = RGB[:, :, 1] * 118
    RGB[:, :, 2] = RGB[:, :, 2] * 235
    RGBA = [RGB[:, :, 0], RGB[:, :, 1], RGB[:, :, 2], alpha]

    src_dilation2 = cv.merge(RGBA, 4)
    return src_dilation2


# edge detect
def edge_from_img(img, threshold_min=160, threshold_max=800):
    # 현재 threshold는 810*1080 사양에 최적화되어 있음
    edge = cv.Canny(img, threshold_min, threshold_max)
    return edge


# resize image; now 1:1 resize
def resize_img(img, resize):
    resize = cv.resize(img, resize)
    return resize


# edge detect and transparent
def process_from_img(img, scale1=4, scale2=4, size=270):
    height = img.shape[0]
    width = img.shape[1]
    if height == width:
        # 1:1비율
        pass
    elif height > width:
        # 세로로 긴 경우
        gap = height - width
        gap_half = int(gap / 2)
        end = height - gap_half
        cropped = img[gap_half:end, :, :]
        img = cropped
    else:
        # 가로로 긴 경우
        gap = width - height
        gap_half = int(gap / 2)
        end = width - gap_half
        cropped = img[:, gap_half:end, :]
        img = cropped

    size_re = (scale1 * size, scale2 * size)

    img_resize = cv.resize(img, size_re)
    src = edge_from_img(img_resize)

    result = afterprocessing(src, filter=5, iterations=2)
    # result = cv.addWeighted(img_resize, 0.5, result, 0.5, 0)
    return result, img_resize


@app.route("/select", methods=["GET"])
def get_guide(id):

    return


# detect edge and save image & save edge in S3
@app.route("/image", methods=["POST"])
def upload_file():
    if "user_file" not in request.files:
        return "No user_file key in request.files"

    file = request.files["user_file"]

    if file.filename == "":
        return "Please select a file"

    if file:
        filename_edge = os.path.splitext(file.filename)[0] + "_edge.png"
        file.filename = secure_filename(file.filename)
        filename_edge = secure_filename(filename_edge)

        file.save(file.filename)

        img = cv.imread(file.filename)

        img_result, img_resize = process_from_img(img)

        edge_serial = cv.imencode(".png", img_result)[1].tobytes()
        img_serial = cv.imencode(".jpg", img_resize)[1].tobytes()

        s3 = s3_connection()

        bool1 = s3.put_object(
            Body=str(edge_serial),
            Bucket=BUCKET_NAME,
            Key=filename_edge,
            ContentType="image/png",
            ACL="private",
        )
        bool2 = s3.put_object(
            Body=str(img_serial),
            Bucket=BUCKET_NAME,
            Key=file.filename,
            ContentType="image/jpg",
            ACL="private",
        )
        db = DB_connection()
        cursor = db.cursor()

        sql = "INSERT INTO public.image_table(owner_id,image_id,image_fname,edge_id,edge_fname) VALUES({owner_id},'{image_id}','{image_fname}','{edge_id}','{edge_fname}')".format(
            owner_id=1,
            image_id=os.path.splitext(file.filename)[0],
            image_fname=file.filename,
            edge_id=os.path.splitext(filename_edge)[0],
            edge_fname=filename_edge,
        )
        cursor.execute(sql)
        db.commit()

        db.close()
        cursor.close()

        return "normal"
    else:
        return "file is abnormal"


if __name__ == "__main__":
    app.run("0.0.0.0", port=8080)
