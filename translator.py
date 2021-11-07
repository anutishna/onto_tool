from argostranslate import package, translate


def generate_code_name(
        text,
        case_type='lowerCamelCase'  # допустимые значения: 'lowerCamelCase', 'CamelCase', 'snake_case'
):
    package.install_from_path('assets/translate-ru_en-1_0.argosmodel')
    installed_languages = translate.get_installed_languages()
    translator = installed_languages[1].get_translation(installed_languages[0])
    translation = translator.translate(text)
    words = translation.split(' ')

    if case_type in ['lowerCamelCase', 'snake_case']:
        name = words[0].lower()
    else:
        name = words[0].capitalize()
    for i in range(0, len(words) - 1):
        if case_type in ['lowerCamelCase', 'CamelCase']:
            name += words[i + 1].capitalize()
        else:
            name += '_' + words[i + 1].lower()
    return name


if __name__ == '__main__':
    print(generate_code_name('управляющая программа для роботов', case_type='snake_case'))
    print(generate_code_name('управляющая программа для роботов', case_type='CamelCase'))
    print(generate_code_name('управляющая программа для роботов', case_type='lowerCamelCase'))
