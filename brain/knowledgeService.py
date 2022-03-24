from neo4j import GraphDatabase


class KnowledgeBase:
    def __init__(self, neo4j_uri = "localhost:7687"):
        self.host = neo4j_uri

    def make_query(self, query_string):
        results = {}
        #with GraknClient(uri=self.grakn_host) as client:
        #    with client.session(keyspace="intro") as session:
        #        
        #        ## creating a read transaction
        #        with session.transaction().read() as read_transaction:
        #            answer_iterator = read_transaction.query("match $x isa person; get; limit 10;").get()
        #            for answer in answer_iterator:
        #                person = answer.map().get("x")
        #                print(person)
        #                print("Retrieved person with id " + person.id)
