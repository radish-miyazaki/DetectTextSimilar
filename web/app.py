from flask import Flask, jsonify, request
from pymongo import MongoClient
import bcrypt
import spacy

app = Flask(__name__)
client = MongoClient("mongodb://db:27017")
db = client["SimilarityDB"]
users = db["Users"]


def user_exist(username):
    if users.find({"Username": username}).count() == 0:
        return False
    else:
        return True


@app.route('/register', methods=['POST'])
def register_users():
    posted_data = request.get_json()

    username = posted_data['username']
    password = posted_data['password']

    if user_exist(username):
        retJson = {
            "status": 301,
            "message": "Invalid Username"
        }
        return jsonify(retJson)

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    users.insert({
        "Username": username,
        "Password": hashed_pw,
        "Tokens": 6
    })

    retJson = {
        "status": 200,
        "Msg": "You've successfully signed up to the API."
    }

    return jsonify(retJson)


def verify_password(username, password):
    if not user_exist(username):
        return False

    hashed_pw = users.find({
        "Username": username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
        return True
    else:
        return False


def count_tokens(username):
    tokens = users.find({
        "Username": username
    })[0]["Tokens"]

    return tokens


@app.route('/detect', methods=['POST'])
def detect_similarity_of_docs():
    posted_data = request.get_json()

    username = posted_data['username']
    password = posted_data['password']
    text1 = posted_data['text1']
    text2 = posted_data['text2']

    if not user_exist(username):
        retJson = {
            "status": 301,
            "message": "Invalid Username"
        }
        return jsonify(retJson)

    correct_pw = verify_password(username, password)

    if not correct_pw:
        retJson = {
            "status": 302,
            "message": "Invalid Password"
        }
        return jsonify(retJson)

    num_tokens = count_tokens(username)

    if num_tokens <= 0:
        retJson = {
            "status": 303,
            "message": "You're out of tokens, please refill!"
        }
        return jsonify(retJson)

    # 実際にspacyを用いて自然言語処理をしている箇所
    # 2つの言葉がどれだけ似ているかを割合化
    nlp = spacy.load('en_core_web_sm')

    text1 = nlp(text1)
    text2 = nlp(text2)

    # ratio is a number between 0 and 1 the closer to 1, the more similar text and text2 are
    ratio = text1.similarity(text2)

    retJson = {
        "status": 200,
        "similarity": ratio,
        "message": "Similarity score calculated successfully"
    }

    current_tokens = count_tokens(username)

    users.update({
        "Username": username
    }, {
        "$set": {
            "Tokens": current_tokens - 1,
        }
    })

    return jsonify(retJson)


@app.route('/refill', methods=['POST'])
def refill():
    posted_data = request.get_json()

    username = posted_data['username']
    password = posted_data['admin_password']
    refill_amount = posted_data['refill']

    if not user_exist(username):
        retJson = {
            "status": 301,
            "message": "Invalid Username"
        }
        return jsonify(retJson)

    # Admin用のパスワード（本来はハードコードしない）
    correct_password = "abc123"

    if not password == correct_password:
        retJson = {
            "status": 304,
            "message": "Invalid Admin Password"
        }
        return jsonify(retJson)

    current_tokens = count_tokens(username)
    users.update({
        "Username": username
    }, {
        "$set": {
            "Tokens": refill_amount + current_tokens
        }
    })

    retJson = {
        "status": 200,
        "message": "Refill successfully"
    }
    return jsonify(retJson)


if __name__ == "__main__":
    app.run(host='0.0.0.0')
