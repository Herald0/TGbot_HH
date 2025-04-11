import asyncio
import aiohttp

from aiogram import Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

import matplotlib.pyplot as plt


router = Router()


class Job(StatesGroup):
    keyword_1 = State()
    keyword_2 = State()


class Weather(StatesGroup):
    city = State()


async def get_key_skills(session, url):
    async with session.get(url) as response:
        extended_vacancy = await response.json()
        if 'key_skills' in extended_vacancy:
            key_skills = [key_skill['name'] for key_skill in extended_vacancy['key_skills']]
            return key_skills


async def number_format(number):
    return '{:,}'.format(number).replace(',', ' ')


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Приветик!')
    await message.answer('Если вы попали сюда, значит вы обогнали 99,99% человек на этой планете'
                         ' и входите в число 2-х человек, у которых есть к нам доступ)')
    await message.answer('Выберите команду из списка ниже')


@router.message(Command('job'))
async def cmd_enter_keyword_1(message: Message, state: FSMContext):
    await state.set_state(Job.keyword_1)
    await message.answer('Введите название профессии или ключевое слово')


@router.message(Job.keyword_1)
async def cmd_job(message: Message, state: FSMContext):
    await state.update_data(keyword_1=message.text)
    keyword = (await state.get_data())['keyword_1']
    await state.clear()

    page_count = 30

    async with aiohttp.ClientSession() as session:

        url = f"https://api.hh.ru/vacancies?text={keyword}&area=1&per_page={page_count}"
        async with session.get(url) as response:

            if not response.ok:
                await message.answer("Ошибка", disable_web_page_preview=True)

            vacancies = (await response.json())['items']
            tasks = []
            mes, s = '', ''

            for vacancy in vacancies:
                url = f"https://api.hh.ru/vacancies/{vacancy['id']}"
                tasks.append(asyncio.ensure_future(get_key_skills(session, url)))

            key_skills = await asyncio.gather(*tasks)

            for i, vacancy in enumerate(vacancies):
                s += f'{i + 1}. {vacancy['name']}\n'

                if vacancy["salary"]:
                    frm = await number_format(vacancy["salary"]["from"]) if vacancy["salary"]["from"] else None
                    to = await number_format(vacancy["salary"]["to"]) if vacancy["salary"]["to"] else None

                    if frm and to:
                        salary = f"от {frm} до {to}"
                    else:
                        salary = f"от {frm}" if frm else f"до {to}"

                    s += f"{salary} RUB\n"

                s += '-' * 28 + '\n'

                s += 'Опыт работы: ' + vacancy['experience']['name'] + '\n\n'

                key_skill = ''
                if key_skills[i]:
                    key_skill = ', '.join(key_skills[i])

                if key_skill != '':
                    s += "Key Skills: " + key_skill + '\n\n'

                s += vacancy["alternate_url"] + '\n\n'
                s += "=" * 28 + '\n'

                if len(mes + s) < 4096:
                    mes += s
                else:
                    await message.answer(mes, disable_web_page_preview=True)
                    mes = s

                s = ''

            if mes == '':
                mes = 'Не найдено вакансий'

            await message.answer(mes, disable_web_page_preview=True)


@router.message(Command('weather'))
async def cmd_enter_city(message: Message, state: FSMContext):
    await state.set_state(Weather.city)
    await message.answer("Введите название города")


@router.message(Weather.city)
async def cmd_weather(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    city = (await state.get_data())['city']
    await state.clear()

    API = "ccf6a25d95d77ff985ae6ae604de8ba3"

    async with aiohttp.ClientSession() as session:

        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API}&units=metric"
        async with session.get(url) as response:
            if response.ok:
                data = await response.json()

                temp = data["main"]["temp"]
                wind = data["wind"]["speed"]

                await message.answer(f"{str(city).capitalize()}\nТемпература: {temp} C\nВетер: {wind} m/s")
            else:
                await message.answer("Некорректное название города")


# @router.message(Command('yumii'))
# async def send_photo(message: Message):
#     file = FSInputFile('img/Юми_лес.png')
#     await message.answer_photo(file)


@router.message(Command('key_skills'))
async def cmd_enter_keyword_2(message: Message, state: FSMContext):
    await state.set_state(Job.keyword_2)
    await message.answer('Введите название профессии или ключевое слово')


@router.message(Job.keyword_2)
async def cmd_enter_count(message: Message, state: FSMContext):
    await state.update_data(keyword_2=message.text)
    keyword = (await state.get_data())['keyword_2']
    await state.clear()

    page_count = 100
    key_skills_count = {}

    async with aiohttp.ClientSession() as session:

        url = f"https://api.hh.ru/vacancies?text={keyword}&area=1&per_page={page_count}"
        async with session.get(url) as response:

            if not response.ok:
                await message.answer("Ошибка")

            vacancies = (await response.json())['items']
            tasks = []

            for vacancy in vacancies:
                url = f"https://api.hh.ru/vacancies/{vacancy['id']}"
                tasks.append(asyncio.ensure_future(get_key_skills(session, url)))

            key_skills_array = await asyncio.gather(*tasks)

            for key_skills in key_skills_array:
                if key_skills is None:
                    continue

                for key_skill in key_skills:
                    if key_skill not in key_skills_count:
                        key_skills_count[key_skill] = 1
                        continue

                    key_skills_count[key_skill] += 1

            diagram_field_count = 10

            sorted_key_skills = sorted(key_skills_count.items(), key=lambda x: x[1], reverse=True)[:diagram_field_count]
            labels = [i[0] for i in sorted_key_skills]
            values = [i[1] for i in sorted_key_skills]

            plt.pie(values, labels=labels, autopct='%1.1f%%')
            plt.savefig('img/diagram.png')
            plt.clf()

            file = FSInputFile('img/diagram.png')
            await message.answer_photo(file)
