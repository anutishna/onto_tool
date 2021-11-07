from csnake import CodeWriter, Function, Variable, Enum
import pandas as pd
from dotenv import load_dotenv
import os


def query_res_to_df(query_res):
    if len(query_res) == 0:
        return pd.DataFrame()
    cols = dict(query_res[0]).keys()
    data = {}
    for col in cols:
        vals = []
        for i in query_res:
            val = dict(i)[col]
            vals.append(val)
        data[col] = vals
    return pd.DataFrame(data=data)


def get_states(conn):
    """Получает все доступные состояния"""
    query = """
MATCH (code:Development:State), 
(code)-[ {name: 'наследоваться от'}]->(solution)
RETURN code.dev_name, solution.name"""
    res = conn.query(query)
    print('get_states', res)
    return {dict(r)['code.dev_name']: dict(r)['solution.name'] for r in res}


def get_states_to_transit(state_name, conn):
    """Получает все связанные состояния с заданным"""
    query = """
MATCH (state_1:State {name: '%s'}), 
(state_1)-[ {name: 'переходить в'}]->(state_2),
(state_2_dev)-[ {name: 'наследоваться от'}]->(state_2)
RETURN state_1.name, state_2.name, state_2_dev.name""" % state_name
    res = conn.query(query)
    print('get_states_to_transit', res)
    return {dict(i)['state_2_dev.name']: dict(i)['state_2.name'] for i in res}


def get_operations_before_transition(state_name, conn):
    """Получает все операции, которые необходимо выполнить до перехода"""
    query = """
MATCH (state_1:State {name: '%s'}), 
(state_1)-[ {name: 'предшествовать'}]->(process_name),
(process_code)-[ {name: 'наследоваться от'}]->(process_name)
RETURN process_name.name as name, process_code.dev_name as codename, labels(process_code) as labels
""" % state_name
    res = conn.query(query)
    print('get_operations_before_transition', res)
    return query_res_to_df(res)
    # return {dict(i)['process_code.codename']: dict(i)['process_name.name'] for i in res}


def get_condition(s_1, s_2, conn):
    """Получает условие перехода"""
    print(s_1, s_2)
    query = """
MATCH (state_1:State {name: '%s'}), (state_2:State {name: '%s'}),
(t)-[ {name: 'быть переходом из'}]->(state_1), (t)-[ {name: 'быть переходом в'}]->(state_2),
(p)-[ {name: 'быть предикатом перехода'}]->(t), (p_code)-[ {name: 'наследоваться от'}]->(p)
RETURN p.name, p_code.dev_name""" % (s_1, s_2)
    print(query)
    res = conn.query(query)
    print('get_condition', res)
    return dict(res[0])['p_code.dev_name'], dict(res[0])['p.name']


def get_operations_after_transition(predicate, conn):
    """Получает все операции, которые необходимо выполнить после перехода"""
    query = """
MATCH (pr:Predicate {name: '%s'}),
(pr)-[ {name: 'быть предикатом перехода'}]->(t),
(t)-[ {name: 'вызывать'}]->(p),
(p_code)-[ {name: 'наследоваться от'}]->(p)
RETURN p.name as name, p_code.dev_name as codename, labels(p_code) as labels""" % predicate
    res = conn.query(query)
    print('get_operations_after_transition', res)
    return query_res_to_df(res)
    # return {dict(i)['p_code.codename']: dict(i)['p.name'] for i in res}


def add_process_lines(p_cwr, df):
    for _, row in df.iterrows():
        line = row['codename']
        if 'Function' in row['labels']:
            line += '()'
        p_cwr.add_line(line+';', comment=row['name'])


def get_code(connection):
    cwr = CodeWriter()

    # состояния
    states = get_states(connection)
    enum = Enum('STATES')
    enum.add_values(states.keys())
    cwr.add_enum(enum)

    # switch
    cwr_switch = CodeWriter()
    var = Variable('state', 'str')

    cwr_switch.start_switch(var)

    for key_state in states:
        # состояние, из которого осуществляется переход
        state_var = Variable(key_state, 'str')
        cwr_switch.add_switch_case(state_var)

        # действие, которое необходимо выполнить до перехода
        pr_before = get_operations_before_transition(states[key_state], connection)
        add_process_lines(cwr_switch, pr_before)

        sts_to_transit = get_states_to_transit(states[key_state], connection)

        for key_state_2 in sts_to_transit:
            # условие перехода
            cond, cond_comm = get_condition(states[key_state], sts_to_transit[key_state_2], connection)
            cwr_switch.add_line('if (%s) {' % cond, comment=cond_comm)
            cwr_switch.indent()

            # изменение состояния
            cwr_switch.add_line('state = %s;' % key_state_2)

            # действие, которое необходимо выполнить после перехода
            pr_after = get_operations_after_transition(cond_comm, connection)
            # print(pr_after)
            add_process_lines(cwr_switch, pr_after)
            cwr_switch.close_brace()

        cwr_switch.add_switch_break()

    # объявляем функцию step()
    step_fun = Function('step', return_type='void')
    step_fun.add_code(cwr_switch)
    cwr.add_function_definition(step_fun)
    connection.close()
    print(cwr)
    cwr.write_to_file('tmp/generated_step.c')

    with open('tmp/generated_step.c') as f:
        return f.read()


if __name__ == '__main__':
    load_dotenv()
    URI = os.getenv("URI")
    USER = os.getenv("USERNAME")
    PASSWORD = os.getenv("PASSWORD")
    # conn = nc.Neo4jConnection(uri=URI, user=USER, pwd=PASSWORD)
    code = get_code(conn)