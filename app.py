from flask import Flask, jsonify, render_template, request, send_from_directory

app = Flask(__name__)

@app.route('/')
def favFE():
    return render_template('base.html')

@app.route('/upload')
def getUpload():
    return render_template('upload.html')

@app.route('/login')
def getLogin():
    return render_template('login.html')

@app.route('/signup')
def getSignUp():
    return render_template('signup.html')

@app.route('/presentations/my')
def getMyPresentations():
    return render_template('myresen.html')

@app.route('/presentations/all')
def getAllPresentations():
    return render_template('all_presentations.html')

if __name__ == '__main__':  
   app.run('0.0.0.0', port=5000, debug=True)