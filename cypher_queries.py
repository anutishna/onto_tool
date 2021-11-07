from dotenv import load_dotenv
import os
import neo4j_db_connector as nc


def create_concept(concept, label):
    """Создание концепта с указанной меткой"""
    return 'MERGE (a:Requirements:%s {name: "%s" })' % (label, concept)


def create_relation(
        main_concept, related_concept, rel_type,
        rel_label='SEM_REL',
        main_concept_label='Requirements',
        related_concept_label='Requirements',
):
    """Создение отношения"""
    query = (
            'MATCH (a:%s {name: "%s"}), (b:%s {name: "%s"})'
            'MERGE (a)-[:%s {name: "%s"}]->(b)' % (
                main_concept_label, main_concept, related_concept_label, related_concept, rel_label, rel_type)
    )
    return query


def clear_data():
    """Очистка данных онтологии"""
    return "MATCH (a) DETACH DELETE a"


def get_requirement_nodes(connection):
    """Поиск всех концептов в онтологии требований"""
    q = 'MATCH (a:Requirements) WHERE NOT(a:Source) RETURN a'
    res = connection.query(q)
    return [dict(r['a'])['name'] for r in res]


def get_sub_query(properties_dict):
    """Генерация подзапроса, содержащего свойства концепта"""
    sub_query = '{'
    for k, v in properties_dict.items():
        sub_query += k + ': '
        if type(v) == str:
            sub_query += '"' + v + '", '
        else:
            sub_query += str(v) + ', '
    return sub_query[:-2] + '}'


def create_state_machine_model(
        label,
        initial_state,
        result_state,
        predicate,
        action_before=None,
        action_after=None,
):
    """Загрузка ОМ, соответствующей проектному решению «Автоматная модель»"""
    transition = {
        'name': 'Переход из состояния «{}» в состояние «{}»'.format(initial_state['name'], result_state['name']),
        'specified': False
    }
    q = [
        'MERGE(state_1:{}:State {})'.format(label, get_sub_query(initial_state)),
        'MERGE(state_2:{}:State {})'.format(label, get_sub_query(result_state)),
        'MERGE(trans:{}:Transition {})'.format(label, get_sub_query(transition)),
        'MERGE(pred:{}:Predicate {})'.format(label, get_sub_query(predicate)),

        'MERGE(state_1) - [:TRANSIT_TO {name: "переходить в"}]->(state_2)',
        'MERGE(trans) - [:BE_TRANSITION_FROM {name: "быть переходом из"}]->(state_1)',
        'MERGE(trans) - [:BE_TRANSITION_TO {name: "быть переходом в"}]->(state_2)',
        'MERGE(pred) - [:BE_PREDICATE {name: "быть предикатом перехода"}]->(trans)',
    ]
    if action_before is not None and 'name' in action_before.keys() and action_before['name'] != '':
        q.extend([
            'MERGE(action_before:{}:Action {})'.format(label, get_sub_query(action_before)),
            'MERGE(action_before) - [:PRECEEDE {name: "предшествовать"}]->(trans)',
        ])
    if action_after is not None and 'name' in action_after.keys() and action_after['name'] != '':
        q.extend([
            'MERGE(action_after:{}:Action {})'.format(label, get_sub_query(action_after)),
            'MERGE(trans) - [:СALL {name: "вызывать"}]->(action_after)',
        ])
    return '\n'.join(q)


def get_required_concepts(connection, label):
    q = "MATCH (a:%s {specified:TRUE}) RETURN a" % label
    res = connection.query(q)
    return {dict(r['a'])['name']: dict(r['a'])['is_optional'] for r in res}


def get_states_and_actions_before(connection, names_type='dev_name'):
    q = (
        "MATCH (t:Development:Transition)-[:BE_TRANSITION_FROM]->(s:Development:State), "
        "(a:Development:Action)-[:PRECEEDE]->(t) "
        "RETURN s, a"
    )
    res = connection.query(q)
    return [(r['s'][names_type], r['a'][names_type]) for r in res]


def get_state_transitions(connection, names_type='dev_name'):
    q = (
        "MATCH (s1:Development:State)-[:TRANSIT_TO]->(s2:Development:State),"
        "(trans)-[:BE_TRANSITION_FROM]->(s1),"
        "(trans)-[:BE_TRANSITION_TO]->(s2),"
        "(pred)-[:BE_PREDICATE]->(trans)"
        "RETURN s1, s2, pred, trans"
    )
    res = connection.query(q)

    transitions = []
    for r in res:
        q2 = "MATCH (trans:Development {name: '%s'}), (trans)-[:`СALL`]-(a) RETURN a" % (r['trans']['name'])
        action_res = connection.query(q2)
        actions = [ra['a'][names_type] for ra in action_res]
        pred = r['pred'][names_type] + ": "
        for ac in actions:
            pred += ac + "; "
        pred = pred[:-2]
        transitions.append((r['s1'][names_type], r['s2'][names_type], pred))
    return transitions


if __name__ == '__main__':
    load_dotenv()
    URI = os.getenv("URI")
    USER = os.getenv("USERNAME")
    PASSWORD = os.getenv("PASSWORD")
    conn = nc.Neo4jConnection(uri=URI, user=USER, pwd=PASSWORD)

    # res = get_required_concepts(conn, "StateMachine")
    # print(type(res['Действие до перехода']))
    # print(create_state_machine_model(action_after={'name': 'f'}))
    print(get_state_transitions(conn))
