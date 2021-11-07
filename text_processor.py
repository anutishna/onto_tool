import nltk
import pandas as pd
import pymorphy2
from collections import Counter
nltk.download('punkt')


def filter_sw(tokens):
    """Фильтрация списка токенов по стоп-словам и токенам, содержащим менее одного символа"""
    fltrd_tokens = []
    for token in tokens:
        if len(token) > 1 and token not in list(pd.read_csv('assets/stopwords.csv').word):
            fltrd_tokens.append(token)
    return fltrd_tokens


def normalize(tokens):
    """Нормализация с помощью библитеки pymorphy2"""
    normalized_tokens = []
    morph = pymorphy2.MorphAnalyzer()

    for token in tokens:
        ps = morph.parse(token)
        nfs = []
        for p in ps:
            nfs.append(p.normal_form)
        nfs_set = set(nfs)
        nf_str = ''
        for nf in nfs_set:
            nf_str = nf + '|'
        normalized_tokens.append(nf_str[:-1])
    return normalized_tokens


def count_frequency(tokens, min_frequency):
    frs = Counter(tokens)
    df = pd.DataFrame(data=frs.items(), columns=['Претендент на понятие', 'Частота'])
    return df[df['Частота'] >= min_frequency].sort_values(by='Частота', ascending=False).reset_index(drop=True)


def get_collocations(tokens, x):
    """Выявление цепочки токенов заданной длины"""
    collocations = []
    i = 0
    while i < len(tokens) - (x - 1):
        collocation = tokens[i:i + x]
        collocations.append(collocation)
        i += 1

    punct_marks = [' ', '.', ',', '!', '?', ':', ';', '-', '«', '»', '"', '…', '(', ')', '/', "''"]
    filtered_colls = []
    for col in collocations:
        is_col = True
        for pm in punct_marks:
            if pm in col:
                is_col = False
        if is_col:
            filtered_colls.append(col)
    return filtered_colls


def add_spaces(collocations):
    """Превращение списка словосочетаний в строковый вид (из списка списка токенов)"""
    text_cols = []

    for col in collocations:
        text_col = ''
        for word in col:
            text_col = text_col + word + ' '
        text_cols.append(text_col[:-1].lower())
    return text_cols


def process_text(text, min_frequency=3):
    tokens = nltk.word_tokenize(text, 'russian')

    filtered_tokens = filter_sw(tokens)
    normalized_tokens = normalize(filtered_tokens)

    cols_2 = get_collocations(tokens, 2)
    text_cols_2 = add_spaces(cols_2)

    cols_3 = get_collocations(tokens, 3)
    text_cols_3 = add_spaces(cols_3)

    p_concepts = normalized_tokens + text_cols_2 + text_cols_3
    return count_frequency(p_concepts, min_frequency)
