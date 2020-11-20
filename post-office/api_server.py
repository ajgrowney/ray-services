from flask import Flask, request
from gmailService import check_mail, read_message, DEFAULT_MAX_EMAILS

## API Server
api = Flask(__name__)

# Query Param: limit { int - optional }
# Query Param: newer_than { str - optional}
@api.route('/mail/messages', methods=['GET'])
def check_mail_route():
    max_read = request.args.get('limit', default=DEFAULT_MAX_EMAILS, type=int)
    newer_than = request.args.get('newer_than', default="1d", type=str)
    since = "newer_than:"+newer_than
    res, err = check_mail(max_read, since)
    
    # Response Hanlding
    if len(err) == 0:
        return { "status": 200, "type": "Message", "results": res, "count": len(res) }
    elif len(res) > 0:
        return { "status": 207, "type": "MessageAndError", "results": res, "errors": err }
    else:
        return { "status": 500, "type": "Error", "results": err }


# Query Param: mark { str - optional }
@api.route('/mail/messages/<message_id>', methods=['GET'])
def read_mail_route(message_id:str):
    mark_read = request.args.get('mark', default=False, type=bool)
    try:
        res = read_message(message_id, mark_read)
        response = {'statusCode': 200, 'type': 'Message', 'results': [res], "count": 1}
    except Exception as e:
        print(e)
        response = {'statusCode': 500, 'type': 'str' }
        response['results'] = [str(e)]
    
    return response


if __name__ == "__main__":
    api.run("0.0.0.0",5055)
