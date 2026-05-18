from flask import Flask, request, render_template_string, redirect, url_for, flash, session
import csv
import datetime
import json
import os
from func import get_agriculture_schedule_free as func

app = Flask(__name__)
app.secret_key = 'garden_secret_key'

settings_file = 'settings.json'

cities = [
    'Москва', 'Санкт-Петербург', 'Уфа', 'Краснодар', 'Сочи',
    'Казань', 'Новосибирск', 'Екатеринбург', 'Ростов-на-Дону',
    'Нижний Новгород', 'Самара', 'Омск', 'Челябинск', 'Воронеж', 'Волгоград'
]


def load_city():
    if os.path.exists(settings_file):
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            return settings.get('city', 'Уфа')
    return 'Уфа'


def save_city(city):
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump({'city': city}, f)


def get_current_city():
    return session.get('city', load_city())


crops_data = [
    {'name': 'Картофель', 'required_temperature': 8, 'watering_frequency': 7, 'fertilizing_frequency': 14, 'days_to_harvest': 90},
    {'name': 'Морковь', 'required_temperature': 5, 'watering_frequency': 10, 'fertilizing_frequency': 21, 'days_to_harvest': 80},
    {'name': 'Огурцы', 'required_temperature': 16, 'watering_frequency': 3, 'fertilizing_frequency': 7, 'days_to_harvest': 55},
    {'name': 'Помидоры', 'required_temperature': 15, 'watering_frequency': 5, 'fertilizing_frequency': 10, 'days_to_harvest': 70},
    {'name': 'Лук', 'required_temperature': 6, 'watering_frequency': 8, 'fertilizing_frequency': 18, 'days_to_harvest': 85},
    {'name': 'Капуста', 'required_temperature': 12, 'watering_frequency': 5, 'fertilizing_frequency': 14, 'days_to_harvest': 100},
    {'name': 'Зелень', 'required_temperature': 10, 'watering_frequency': 4, 'fertilizing_frequency': 12, 'days_to_harvest': 40},
    {'name': 'Чеснок', 'required_temperature': 4, 'watering_frequency': 9, 'fertilizing_frequency': 20, 'days_to_harvest': 110},
    {'name': 'Свекла', 'required_temperature': 7, 'watering_frequency': 8, 'fertilizing_frequency': 16, 'days_to_harvest': 75},
    {'name': 'Кабачки', 'required_temperature': 14, 'watering_frequency': 4, 'fertilizing_frequency': 9, 'days_to_harvest': 50}
]

if os.path.exists('crops_data.json'):
    with open('crops_data.json', 'r', encoding='utf-8') as f:
        saved = json.load(f)
        for crop in saved:
            if not any(c['name'] == crop['name'] for c in crops_data):
                crops_data.append(crop)

csv_file = 'my_crop.csv'
if not os.path.exists(csv_file):
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Культура', 'Посадка', 'Полив', 'Удобрение', 'Сбор урожая'])


def format_date(date_str):
    try:
        if '-' in date_str:
            d = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        else:
            d = datetime.datetime.strptime(date_str, '%d.%m.%Y')
        return d.strftime('%d.%m.%Y')
    except:
        return date_str

# основная бизнес логика


def find_crop(name):
    for c in crops_data:
        if c['name'].lower() == name.lower():
            return c
    return None


def get_garden():
    rows = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if row and len(row) >= 5:
                rows.append(row)
    return rows


def crop_exists(name):
    return any(row[0].lower() == name.lower() for row in get_garden())


def add_crop(crop):
    try:
        city = get_current_city()
        result = func(city, crop)
        if not isinstance(result, dict):
            return False, "Ошибка API"
        s = result.get('schedule', {})
        row = [
            crop['name'],
            format_date(s.get('planting', '')),
            format_date(s.get('next_watering', '')),
            format_date(s.get('next_fertilizing', '')),
            format_date(s.get('harvesting', ''))
        ]
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(row)
        return True, f"{crop['name']} добавлен (город: {city})"
    except Exception as e:
        return False, str(e)


def recalculation_dates():
    rows = get_garden()
    if not rows:
        return [], False

    new_rows = []
    changes = []
    city = get_current_city()

    for row in rows:
        crop_name = row[0]
        crop_data = find_crop(crop_name)
        if not crop_data:
            new_rows.append(row)
            continue

        try:
            result = func(city, crop_data)
            if isinstance(result, dict):
                s = result.get('schedule', {})
                new_row = [
                    crop_data['name'],
                    format_date(s.get('planting', '')),
                    format_date(s.get('next_watering', '')),
                    format_date(s.get('next_fertilizing', '')),
                    format_date(s.get('harvesting', ''))
                ]
                if new_row != row:
                    changes.append(f"{crop_name}: даты обновлены для города {city}")
                new_rows.append(new_row)
            else:
                new_rows.append(row)
        except:
            new_rows.append(row)

    if changes:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['Культура', 'Посадка', 'Полив', 'Удобрение', 'Сбор урожая'])
            w.writerows(new_rows)

    return changes, len(changes) > 0


def update_crop_dates():
    rows = get_garden()
    if not rows:
        return []

    today = datetime.datetime.now().date()
    updated = False
    log = []

    for i, row in enumerate(rows):
        crop = find_crop(row[0])
        if not crop:
            continue

        try:
            plant = datetime.datetime.strptime(row[1], '%d.%m.%Y').date()
            water = datetime.datetime.strptime(row[2], '%d.%m.%Y').date()
            fertil = datetime.datetime.strptime(row[3], '%d.%m.%Y').date()
            harvest = datetime.datetime.strptime(row[4], '%d.%m.%Y').date()

            changes = []

            if today >= water:
                days = (today - plant).days
                n = ((days // crop['watering_frequency']) + 1) * crop['watering_frequency']
                new = plant + datetime.timedelta(days=n)
                row[2] = new.strftime('%d.%m.%Y')
                changes.append(f"полив: {water.strftime('%d.%m.%Y')} → {row[2]}")
                updated = True

            if today >= fertil:
                days = (today - plant).days
                n = ((days // crop['fertilizing_frequency']) + 1) * crop['fertilizing_frequency']
                new = plant + datetime.timedelta(days=n)
                row[3] = new.strftime('%d.%m.%Y')
                changes.append(f"удобрение: {fertil.strftime('%d.%m.%Y')} → {row[3]}")
                updated = True

            if today >= harvest:
                changes.append(f"УРОЖАЙ ГОТОВ! (с {row[4]})")

            if changes:
                log.append(f"{row[0]}: {', '.join(changes)}")
                rows[i] = row
        except:
            continue

    if updated:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['Культура', 'Посадка', 'Полив', 'Удобрение', 'Сбор урожая'])
            w.writerows(rows)

    return log


# html


def show_page(content):
    city = get_current_city()
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Садовый помощник</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        .sidebar { background: #2e7d32; min-height: 100vh; }
        .sidebar a { color: white; text-decoration: none; display: block; padding: 12px 20px; transition: 0.3s; }
        .sidebar a:hover { background: #1b5e20; }
        .card { border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .btn-success { background: #4caf50; border: none; }
        .btn-success:hover { background: #2e7d32; }
        .table th { background: #4caf50; color: white; }
        .city-badge { position: fixed; top: 10px; right: 20px; z-index: 1000; }
    </style>
</head>
<body>
    <div class="city-badge">
        <div class="dropdown">
            <button class="btn btn-light btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown">
                <i class="bi bi-geo-alt"></i> {{ city }}
            </button>
            <ul class="dropdown-menu dropdown-menu-end">
                <li><a class="dropdown-item" href="/change_city"><i class="bi bi-pencil"></i> Сменить город</a></li>
            </ul>
        </div>
    </div>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-3 col-lg-2 sidebar p-0">
                <div class="text-center py-4"><h3 class="text-white">🌱 Садовый<br>помощник</h3></div>
                <a href="/"><i class="bi bi-tree"></i> Мой огород</a>
                <a href="/about"><i class="bi bi-info-circle"></i> О программе</a>
                <a href="/feedback"><i class="bi bi-envelope"></i> Обратная связь</a>
                <hr class="bg-light m-2">
                <a href="/profile"><i class="bi bi-person-circle"></i> Личный кабинет</a>
            </div>
            <div class="col-md-9 col-lg-10 p-4">
                {% with msg = get_flashed_messages() %}
                    {% if msg %}<div class="alert alert-success alert-dismissible fade show" role="alert">{{ msg[0]|safe }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>{% endif %}
                {% endwith %}
                ''' + content + '''
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
''', city=city)


@app.route('/change_city', methods=['GET', 'POST'])
def change_city():
    if request.method == 'POST':
        city = request.form.get('city')
        if city and city in cities:
            old_city = get_current_city()
            save_city(city)
            session['city'] = city
            changes, updated = recalculation_dates()
            if updated:
                flash(f'Город изменён с {old_city} на {city}. Даты посадки пересчитаны!', 'success')
                if changes:
                    flash('<br>'.join(changes), 'info')
            else:
                flash(f'Город изменён на {city}', 'success')
            return redirect(url_for('garden'))
        else:
            flash('Пожалуйста, выберите город из списка', 'danger')

    current_city = get_current_city()
    city_options = ''
    for c in cities:
        selected = 'selected' if c == current_city else ''
        city_options += f'<option value="{c}" {selected}>{c}</option>'

    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Выбор города - Садовый помощник</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .city-card { max-width: 500px; margin: 100px auto; border-radius: 20px; }
        select.form-select { cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card city-card shadow">
            <div class="card-body p-5">
                <div class="text-center mb-4">
                    <i class="bi bi-geo-alt text-success" style="font-size: 3rem;"></i>
                    <h2 class="text-success mt-2">Выбор города</h2>
                    <p class="text-muted">Для точного расчёта дат посадки</p>
                </div>
                <form method="post">
                    <div class="mb-3">
                        <label class="form-label">Ваш город</label>
                        <select name="city" class="form-select form-select-lg" required>
                            <option value="">-- Выберите город --</option>
                            ''' + city_options + '''
                        </select>
                    </div>
                    <button type="submit" class="btn btn-success w-100 btn-lg">Сохранить</button>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
''')


@app.route('/')
def garden():
    if not os.path.exists(settings_file) and 'city' not in session:
        return redirect(url_for('change_city'))

    rows = get_garden()
    if rows:
        table_rows = ''
        for r in rows:
            table_rows += '<tr>'
            for c in r:
                table_rows += f'<td>{c}</td>'
            table_rows += '</tr>'
        content = f'''
        <div class="card p-4">
            <h2 class="text-success"><i class="bi bi-tree"></i> Мой огород</h2>
            <div class="table-responsive">
                <table class="table table-bordered table-hover">
                    <thead><tr><th>Культура</th><th>Посадка</th><th>Полив</th><th>Удобрение</th><th>Сбор урожая</th></tr></thead>
                    <tbody>{table_rows}</tbody>
                </table>
            </div>
            <div class="mt-3">
                <a href="/choice" class="btn btn-success"><i class="bi bi-plus-circle"></i> Добавить культуру</a>
                <a href="/update" class="btn btn-outline-success"><i class="bi bi-arrow-repeat"></i> Обновить даты</a>
            </div>
        </div>
        '''
    else:
        content = '''
        <div class="card p-4">
            <h2 class="text-success"><i class="bi bi-tree"></i> Мой огород</h2>
            <div class="alert alert-info text-center">🌱 Огород пуст. Добавьте культуры!</div>
            <div class="mt-3">
                <a href="/choice" class="btn btn-success"><i class="bi bi-plus-circle"></i> Добавить культуру</a>
                <a href="/update" class="btn btn-outline-success"><i class="bi bi-arrow-repeat"></i> Обновить даты</a>
            </div>
        </div>
        '''
    return show_page(content)


@app.route('/choice')
def choice():
    content = '''
    <div class="card p-4 text-center">
        <h2 class="text-success"><i class="bi bi-question-circle"></i> Выберите действие</h2>
        <div class="row mt-4">
            <div class="col-md-6"><a href="/list" class="btn btn-success btn-lg w-100 py-3"><i class="bi bi-book"></i> Выбрать из базы</a></div>
            <div class="col-md-6"><a href="/new" class="btn btn-outline-success btn-lg w-100 py-3"><i class="bi bi-plus-circle"></i> Добавить свою</a></div>
        </div>
    </div>
    '''
    return show_page(content)


@app.route('/list')
def list_crops():
    cards = ''
    for c in crops_data:
        cards += f'''
        <div class="col-md-4 mb-3">
            <div class="card h-100">
                <div class="card-body text-center">
                    <h4>{c['name']}</h4>
                    <p><i class="bi bi-thermometer-half"></i> {c['required_temperature']}°C</p>
                    <p><i class="bi bi-droplet"></i> Полив: каждые {c['watering_frequency']} дн.</p>
                    <p><i class="bi bi-flower1"></i> Удобрение: каждые {c['fertilizing_frequency']} дн.</p>
                    <p><i class="bi bi-calendar-check"></i> Сбор: через {c['days_to_harvest']} дн.</p>
                    <form method="post" action="/add"><input type="hidden" name="name" value="{c['name']}"><button class="btn btn-success w-100"><i class="bi bi-plus-circle"></i> Добавить</button></form>
                </div>
            </div>
        </div>
        '''
    content = f'''
    <div class="card p-4">
        <h2 class="text-success"><i class="bi bi-book"></i> База культур</h2>
        <div class="row mt-3">
            {cards}
        </div>
        <a href="/choice" class="btn btn-secondary"><i class="bi bi-arrow-left"></i> Назад</a>
    </div>
    '''
    return show_page(content)


@app.route('/new')
def new_crop():
    content = '''
    <div class="card p-4" style="max-width:500px; margin:0 auto;">
        <h2 class="text-success"><i class="bi bi-plus-circle"></i> Создание культуры</h2>
        <form method="post" action="/create">
            <div class="mb-3"><label class="form-label">Название</label><input name="name" class="form-control" required></div>
            <div class="mb-3"><label class="form-label">Температура (°C)</label><input name="temp" type="number" class="form-control" required></div>
            <div class="mb-3"><label class="form-label">Полив (дней)</label><input name="water" type="number" class="form-control" required></div>
            <div class="mb-3"><label class="form-label">Удобрение (дней)</label><input name="fertil" type="number" class="form-control" required></div>
            <div class="mb-3"><label class="form-label">Сбор урожая (дней)</label><input name="harvest" type="number" class="form-control" required></div>
            <button type="submit" class="btn btn-success w-100"><i class="bi bi-check-circle"></i> Создать</button>
            <a href="/choice" class="btn btn-secondary w-100 mt-2"><i class="bi bi-arrow-left"></i> Назад</a>
        </form>
    </div>
    '''
    return show_page(content)


@app.route('/about')
def about():
    content = '''
    <div class="card p-4">
        <h2 class="text-success"><i class="bi bi-info-circle"></i> О программе</h2>
        <p><strong>"Садовый Помощник"</strong> — приложение для садоводов и огородников.</p>
        <p>Помогает определить оптимальные сроки посадки и ухода за культурами на основе погодных данных.</p>
        <hr><p>© 2024 | Версия 1.0</p>
    </div>
    '''
    return show_page(content)


@app.route('/feedback')
def feedback():
    content = '''
    <div class="card p-4 text-center">
        <h2 class="text-success"><i class="bi bi-envelope"></i> Обратная связь</h2>
        <div class="bg-light p-4 rounded mt-3"><i class="bi bi-mailbox fs-1"></i><p class="mt-3">Email: <strong>assistantgarden@yandex.ru</strong></p></div>
    </div>
    '''
    return show_page(content)


@app.route('/profile')
def profile():
    city = get_current_city()
    content = f'''
    <div class="card p-4" style="background: linear-gradient(135deg, #667eea, #764ba2); color: white;">
        <h2><i class="bi bi-person-circle"></i> Мой профиль</h2>
        <div class="mt-3">
            <p><strong>Имя:</strong> Арслан</p>
            <p><strong>Email:</strong> arslan@chupakabra.ru</p>
            <p><strong>Регион:</strong> {city}</p>
        </div>
        <a href="/change_city" class="btn btn-light mt-3"><i class="bi bi-geo-alt"></i> Сменить город</a>
        <a href="/" class="btn btn-outline-light mt-2"><i class="bi bi-tree"></i> В огород</a>
    </div>
    '''
    return show_page(content)


@app.route('/add', methods=['POST'])
def add():
    name = request.form.get('name')
    crop = find_crop(name)
    if not crop:
        flash('Культура не найдена')
    elif crop_exists(name):
        flash(f'Культура "{name}" уже есть в огороде!')
    else:
        success, msg = add_crop(crop)
        flash(msg)
    return redirect(url_for('garden'))


@app.route('/update')
def update():
    log = update_crop_dates()
    if log:
        flash('<br>'.join(log))
    else:
        flash('Все даты актуальны')
    return redirect(url_for('garden'))


@app.route('/create', methods=['POST'])
def create():
    name = request.form.get('name', '').strip()
    try:
        new_crop = {
            'name': name,
            'required_temperature': int(request.form.get('temp')),
            'watering_frequency': int(request.form.get('water')),
            'fertilizing_frequency': int(request.form.get('fertil')),
            'days_to_harvest': int(request.form.get('harvest'))
        }
        if find_crop(name):
            flash(f'Культура "{name}" уже существует!')
        else:
            crops_data.append(new_crop)
            with open('crops_data.json', 'w', encoding='utf-8') as f:
                json.dump(crops_data, f, ensure_ascii=False, indent=2)
            flash(f'Культура "{name}" создана!')
    except Exception as e:
        flash(f'Ошибка: {e}')
    return redirect(url_for('garden'))


if __name__ == '__main__':
    print("http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
