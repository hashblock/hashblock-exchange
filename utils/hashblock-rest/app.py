from flask import Flask
from flask_restplus import Resource, Api

application = Flask(__name__)
api = Api(application,
          version='0.1',
          title='Our sample API',
          description='This is our sample API',)


@api.route('/hello')
class HelloWorld(Resource):
    def get(self):
        return {'hello': 'world',
                'sawtooth-response': 'tbd'}


if __name__ == '__main__':
    application.run(debug=True)
