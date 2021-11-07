import cypher_queries as cq
from dotenv import load_dotenv
import os
import neo4j_db_connector as nc
import subprocess


def get_state_diagram(connection):
    uml_desc = ['@startuml']

    states = cq.get_states_and_actions_before(connection, names_type='dev_name')
    for state in states:
        uml_str = 'state "{}" : {}'.format(state[0], state[1])
        if not (uml_str in uml_desc):
            uml_desc.append(uml_str)

    transitions = cq.get_state_transitions(connection, names_type='dev_name')
    for trans in transitions:
        uml_str = "{} --> {}: {}".format(trans[0], trans[1], trans[2])
        if not (uml_str in uml_desc):
            uml_desc.append(uml_str)

    uml_desc.append("@enduml")
    return '\n'.join(uml_desc)


def generate_diagram(connection):
    uml_declaration = get_state_diagram(connection)
    print(uml_declaration)
    connection.close()
    with open('tmp/uml_declaration.txt', 'w') as f:
        f.write(uml_declaration)
    subprocess.call(['java', '-jar', 'assets/plantuml.jar', 'tmp/uml_declaration.txt'])
    return 'tmp/uml_declaration.png'


if __name__ == '__main__':
    load_dotenv()
    URI = os.getenv("URI")
    USER = os.getenv("USERNAME")
    PASSWORD = os.getenv("PASSWORD")
    conn = nc.Neo4jConnection(uri=URI, user=USER, pwd=PASSWORD)

    uml_decl = get_state_diagram(conn)
    conn.close()

    print(uml_decl)

    with open('tmp/uml_declaration.txt', 'w') as f:
        f.write(uml_decl)
    subprocess.call(['java', '-jar', 'assets/plantuml.jar', 'tmp/uml_declaration.txt'])
