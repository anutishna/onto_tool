from dotenv import load_dotenv
import os
import neo4j_db_connector as nc


def get_transition_info(s_from, s_to, info_type):
    q = [
        "MATCH (a:Solutions:State {name: '%s'})-[:TRANSIT_TO]->(b:Solutions:State {name: '%s'}), " % (s_from, s_to),
        "(t)-[:BE_TRANSITION_FROM]->(a), ",
        "(t)-[:BE_TRANSITION_TO]->(b), ",
        "(pred:Solutions)-[:BE_PREDICATE]->(t)"
    ]
    if info_type == 'predicate':
        q.append(" RETURN pred")
    if info_type == 'action':
        q.append(", (t)-[:`СALL`]->(action) RETURN action")
    if info_type == 'pr_action':
        q.append(", (action)-[:PRECEEDE]->(t) RETURN action")
    return ''.join(q)


def get_doc(connection):
    doc = ['Реализация СЛУ должна предусматривать следующие состояния:']
    states_result = connection.query('MATCH (a:Solutions:State) RETURN a')
    states = [dict(s['a'])['name'] for s in states_result]
    doc.extend(['- ' + s + ';' for s in states])

    for state in states:
        trans_res = connection.query("MATCH (a:Solutions:State {name: '%s'})-[:TRANSIT_TO]->(b) RETURN a, b" % state)
        transitions = [(dict(t['a'])['name'], dict(t['b'])['name']) for t in trans_res]
        if len(transitions) != 0:
            for trans in transitions:
                if trans[0] != trans[1]:
                    doc.append('\nПереход из состояния «{}» в состояние «{}»'.format(trans[0], trans[1])
                               + ' должен осуществляться при следующих условиях:')

                    tr_info = connection.query(get_transition_info(trans[0], trans[1], 'predicate'))
                    preds = [dict(i['pred'])['name'] for i in tr_info]
                    doc.extend('- ' + pr + ';' for pr in preds)

                    action_types = ['action', 'pr_action']
                    for action_type in action_types:
                        actions_res = connection.query(get_transition_info(trans[0], trans[1], action_type))
                        actions = [dict(i['action'])['name'] for i in actions_res]
                        if len(actions) != 0:
                            ps = 'До' if action_type == 'pr_action' else 'После'
                            doc.append("{} перехода из состояния «{}» в состояние «{}»".format(ps, trans[0], trans[1])
                                       + " должны осуществляться следующие действия:")
                            doc.extend(['- ' + a + ';' for a in actions])

    return '\n'.join(doc)


if __name__ == '__main__':
    load_dotenv()
    URI = os.getenv("URI")
    USER = os.getenv("USERNAME")
    PASSWORD = os.getenv("PASSWORD")
    conn = nc.Neo4jConnection(uri=URI, user=USER, pwd=PASSWORD)
    with open('tmp/test_doc.txt', 'w') as f:
        f.write(get_doc(conn))
    conn.close()
