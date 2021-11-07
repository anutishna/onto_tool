import streamlit as st
from text_processor import process_text
import neo4j_db_connector as nc
import pandas as pd
# from dotenv import load_dotenv
import os
import cypher_queries as qs
from translator import generate_code_name
from uml_generator import generate_diagram
from code_generator import get_code
from doc_generator import get_doc

menu = ["Настройки", "Онтология требований", "Онтология проектных решений и реализации", "Генерация документации",
        "Геренация UML", "Генерация кода"]
choice = st.sidebar.selectbox("Menu", menu)


# load_dotenv()
URI = os.getenv("URI")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
try:
    conn = nc.Neo4jConnection(uri=URI, user=USERNAME, pwd=PASSWORD)
    existing_concepts = qs.get_requirement_nodes(conn)
except:
    print('Error: Database not connected')

if choice == "Настройки":
    st.title("Настройки")
    with st.form(key='db_connection') as f:
        st.subheader("Подключение к базе данных")
        uri = st.text_input(label='URI', value='neo4j+s://00000000.databases.neo4j.io', key='uri')
        username = st.text_input(label='Username', value='neo4j', key='username')
        password = st.text_input(label='Password', key='pass')
        submitted = st.form_submit_button('Подключиться')
        if submitted:
            os.environ['URI'] = uri
            os.environ['USERNAME'] = username
            os.environ['PASSWORD'] = password

    add_state_machine = st.button('Добавить проектное решение «Автоматная модель»')
    if add_state_machine:
        conn.query(qs.create_state_machine_model(
            label='StateMachine',
            initial_state={'name': 'Исходное состояние', 'specified': True, 'is_optional': False},
            result_state={'name': 'Результирующее состояние', 'specified': True, 'is_optional': False},
            predicate={'name': 'Условие перехода', 'specified': True, 'is_optional': False},
            action_before={'name': 'Действие до перехода', 'specified': True, 'is_optional': True},
            action_after={'name': 'Действие после перехода', 'specified': True, 'is_optional': True},
        ))
        st.text('В онтологию добавлено проектное решение «Автоматная модель»')
    clear_data = st.button('Очистить онтологию')
    if clear_data:
        conn.query(qs.clear_data())
        st.text('Все данные удалены из онтологии.')

if choice == "Онтология требований":
    if 'count' not in st.session_state:
        st.session_state.count = 0

    st.title("Онтология требований")
    source = st.text_area("Source", height=200)
    min_frequency = st.number_input("Минимальная частота", min_value=1)

    if st.button('Предложить понятия'):
        st.session_state.count = 1

    if st.session_state.count == 0:
        p_concepts = pd.DataFrame()
    else:
        p_concepts = process_text(source, min_frequency=min_frequency)
        # исключение того, что уже есть в онтологии
        p_concepts = p_concepts[p_concepts['Претендент на понятие'].isin(existing_concepts) == False]

    add_info = {}

    # форма с претендентами на включение в онтологию
    with st.form(key='p_concepts') as f:
        st.subheader('Претенденты на включение в онтологию')
        cols = st.beta_columns([1, 3, 2, 1])
        cols[0].markdown('**Частота**')
        cols[1].markdown('**Понятие**')
        cols[2].markdown('**Тип понятия**')
        cols[3].markdown('**Добавить**')

        key_box = 0
        for _, row in p_concepts.iterrows():
            concept = row['Претендент на понятие']
            cols = st.beta_columns([1, 3, 2, 1])
            edited_concept = cols[1].text_input('Понятие', value=concept)
            cols[0].markdown('[{}]'.format(row['Частота']))
            concept_type = cols[2].selectbox(
                'Тип',
                ['Inputs', 'Outputs', 'Actions', 'Events', 'Messages', 'Conditions', 'Processes', 'Protocols'],
                key=concept
            )
            add = cols[3].checkbox('', key=str(key_box))
            key_box += 1
            if add:
                add_info[edited_concept] = concept_type

        submitted = st.form_submit_button('Добавить выбранное в онтологию')
        if submitted:
            source_str = source.replace('"', '')
            if len(add_info) > 0:
                conn.query(qs.create_concept(source_str, 'Source'))
            for concept, label in add_info.items():
                conn.query(qs.create_concept(concept, label))
                conn.query(qs.create_relation(source_str, concept, 'быть источником', rel_label='SERVICE'))
            st.text("В онтологию добавлены следующие концепты:")
            st.text('\n'.join([('{}: {}'.format(k, v)) for k, v in add_info.items()]))

    # форма для добавления связей
    with st.form(key='relations') as f:
        st.subheader('Добавление отношений')
        cols = st.beta_columns([1, 1, 1])

        existing_concepts = qs.get_requirement_nodes(conn)
        main_concept = cols[0].selectbox('Главное понятие', existing_concepts)
        related_concept = cols[2].selectbox('Зависимое понятие', existing_concepts)
        rel_type = cols[1].text_input('Тип отношения')

        submitted = st.form_submit_button('Добавить в онтологию')
        if submitted:
            conn.query(qs.create_relation(main_concept, related_concept, rel_type))
            st.text("В онтологию добавлено отношение «%s» между концептами «%s» и «%s»." % (
                rel_type, main_concept, related_concept))

if choice == "Онтология проектных решений и реализации":
    if 'count' not in st.session_state:
        st.session_state.count = 0

    st.title("Онтология проектных решений и реализации")
    required_concepts = qs.get_required_concepts(conn, "StateMachine")
    state_element = {}

    # форма для наполнения онтологии проектирования
    with st.form(key='state_machine'):
        st.subheader('Добавление элемента автоматной модели в онтологию проектирования')
        cols = st.beta_columns([1, 1])

        relations = []
        key_input = 0
        for concept in required_concepts.keys():
            if required_concepts[concept]:
                new_concept = cols[0].selectbox(
                    concept, key=concept, options=[''] + existing_concepts,
                    help='Необязательное поле'
                )
            else:
                new_concept = cols[0].selectbox(concept, key=concept, options=existing_concepts)
            sol_concept = cols[1].text_input('Имя в онтологии проектирования', key=str(key_input),
                                             help='Можно оставить пустым, если имя должно сохраниться.')
            state_element[concept] = new_concept if sol_concept == '' else sol_concept
            if new_concept != '':
                relations.append((new_concept, new_concept if sol_concept == '' else sol_concept))
            key_input += 1

        case_type = st.selectbox('Тип имён для онтологии реализации',
                                 options=['lowerCamelCase', 'CamelCase', 'snake_case'])

        submitted = st.form_submit_button('Добавить в онтологию')
        if submitted:
            conn.query(qs.create_state_machine_model(
                label='Solutions',
                initial_state={'name': state_element['Исходное состояние']},
                result_state={'name': state_element['Результирующее состояние']},
                predicate={'name': state_element['Условие перехода']},
                action_before={'name': state_element['Действие до перехода']},
                action_after={'name': state_element['Действие после перехода']},
            ))
            st.text('В онтологию проектирования добавлены следующие концепты:')
            st.text('\n'.join([('{}: {}'.format(k, v)) for k, v in state_element.items()]))

            for relation in relations:
                conn.query(qs.create_relation(
                    relation[1], relation[0], 'наследоваться от', rel_label='SERVICE',
                    main_concept_label='Solutions'
                ))
            st.session_state.count = 1

    if st.session_state.count == 0:
        state_element = {}

    # форма для наполнения онтологии проектирования
    with st.form(key='state_machine_dev'):
        st.subheader('Добавление элемента автоматной модели в онтологию реализации')
        key_dev_input = 1000
        dev_concepts = {}
        relations = []

        for sol_type, sol_concept in state_element.items():
            cols = st.beta_columns([1, 1])
            concept_name = cols[0].text_input(sol_type, value=sol_concept, key=str(key_dev_input))
            dev_name = cols[1].text_input(
                'Имя в исходном коде', value=generate_code_name(sol_concept, case_type=case_type),
                key=str(key_dev_input + 1))
            key_dev_input += 2
            dev_concepts[sol_type] = {'name': concept_name, 'dev_name': dev_name}
            if concept_name != '':
                relations.append((sol_concept, concept_name))
        submitted = st.form_submit_button('Добавить в онтологию')

        if submitted:
            conn.query(qs.create_state_machine_model(
                label='Development',
                initial_state=dev_concepts['Исходное состояние'],
                result_state=dev_concepts['Результирующее состояние'],
                predicate=dev_concepts['Условие перехода'],
                action_before=dev_concepts['Действие до перехода'],
                action_after=dev_concepts['Действие после перехода'],
            ))
            st.text('В онтологию проектирования добавлены следующие концепты:')
            st.text('\n'.join([('{}: {}'.format(k, v)) for k, v in dev_concepts.items()]))

            for relation in relations:
                conn.query(qs.create_relation(
                    relation[1], relation[0], 'наследоваться от', rel_label='SERVICE',
                    main_concept_label='Development', related_concept_label='Solutions'
                ))

if choice == "Геренация UML":
    st.title("Геренация UML")
    generate_state_diag = st.button('Сгенерировать диаграмму состояний')
    if generate_state_diag:
        path_to_uml = generate_diagram(conn)
        st.image(path_to_uml)

if choice == "Генерация кода":
    st.title("Геренация кода")
    generate_сode = st.button('Сгенерировать код')
    if generate_сode:
        code = get_code(conn)
        st.code(code)

if choice == "Генерация документации":
    st.title("Геренация документации")
    generate_doc = st.button('Сгенерировать документацию')
    if generate_doc:
        doc = get_doc(conn)
        st.markdown(doc)

conn.close()
