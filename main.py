from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import ImageMessage, MessageEvent, TextMessage, TextSendMessage
import requests, json, os, io, cv2
from io import BytesIO
from PIL import Image
import numpy as np
from keras.models import load_model

app = Flask(__name__)

YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

header = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + YOUR_CHANNEL_ACCESS_TOKEN
}

# model はグローバルで宣言し、初期化しておく
model = None

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# テキストを受け取る部分
@handler.add(MessageEvent, message=TextMessage)
def handler_message(event):
     line_bot_api.reply_message(
         event.reply_token,
         TextSendMessage(text=event.message.text))

# オウム返しする部分。おまけ。
def reply_message(event, messages):
    line_bot_api.reply_message(
        event.reply_token,
        messages=messages,
    )

# 画像を受け取る部分
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    print("handle_image:", event)

    message_id = event.message.id
    getImageLine(message_id)

    try:
        image_text = get_text_by_ms(image_url=getImageLine(message_id))

        messages = [
            TextSendMessage(text=image_text),
        ]

        reply_message(event, messages)

    except Exception as e:
        reply_message(event, TextSendMessage(text='エラーが発生しました'))

def getImageLine(id):

    line_url = 'https://api.line.me/v2/bot/message/' + id + '/content/'

    # 画像の取得
    result = requests.get(line_url, headers=header)
    print(result)

    # 画像の保存
    im = Image.open(BytesIO(result.content))
    filename = '/tmp/' + id + '.jpg'
    print(filename)
    im.save(filename)

    return filename


def get_text_by_ms(image_url):

    # 90行目で保存した url から画像を書き出す。
    image = cv2.imread(image_url)
    if image is None:
        print("Not open")
    b,g,r = cv2.split(image)
    image = cv2.merge([r,g,b])
    img = cv2.resize(image,(64,64))
    img=np.expand_dims(img,axis=0)
    face = detect_who(img=img)

    text = face
    return text

def detect_who(img):

    face=""
    # グローバル変数を取得する
    global model

    # 一番初めだけ model をロードしたい
    if model is None:
        model = load_model('./shiogao_model2.h5')

    predict = model.predict(img)
    faceNumLabel=np.argmax(predict)

    if faceNumLabel == 0:
        face = "オリーブオイル顔"
    elif faceNumLabel == 1:
        face = "塩顔"
    elif faceNumLabel == 2:
        face = "しょうゆ顔"
    elif faceNumLabel == 3:
        face = "ソース顔"
    return face

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
