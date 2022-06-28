import os
import requests
import datetime
import json
from tqdm import tqdm


def get_token_id(file_name):
    """Чтение токена и ID пользователя из файла (записаны построчно)"""
    with open(os.path.join(os.getcwd(), file_name), 'r') as token_file:
        token = token_file.readline().strip()
        id_one = token_file.readline().strip()
    return [token, id_one]


def find_max_dpi(dict_in_search):
    """Максимальное фото"""
    max_dpi = 0
    need_elem = 0
    for j in range(len(dict_in_search)):
        file_dpi = dict_in_search[j].get('width') * dict_in_search[j].get('height')
        if file_dpi > max_dpi:
            max_dpi = file_dpi
            need_elem = j
    return dict_in_search[need_elem].get('url'), dict_in_search[need_elem].get('type')


def time_convert(time_unix):
    """Дата загрузки фото в привычный формат"""
    time_bc = datetime.datetime.fromtimestamp(time_unix)
    str_time = time_bc.strftime('%Y-%m-%d time %H-%M-%S')
    return str_time


class VkParams:
    """Получение параметров запроса для VK"""
    def __init__(self, token_list, version='5.131'):
        self.token = token_list[0]
        self.id = token_list[1]
        self.version = version
        self.start_params = {'access_token': self.token, 'v': self.version}
        self.json, self.export_dict = self._sort_info()

    def _get_photo_info(self):
        """Получение данных о фото"""
        url = 'https://api.vk.com/method/photos.get'
        params = {'owner_id': self.id,
                  'album_id': 'profile',
                  'photo_sizes': 1,
                  'extended': 1,
                  'rev': 1
                  }
        photo_info = requests.get(url, params={**self.start_params, **params}).json()['response']
        return photo_info['count'], photo_info['items']

    def _get_logs_only(self):
        """Данные о фото - в словарь"""
        photo_count, photo_items = self._get_photo_info()
        photo_params = {}
        for i in range(photo_count):
            likes_count = photo_items[i]['likes']['count']
            url_download, picture_size = find_max_dpi(photo_items[i]['sizes'])
            time_warp = time_convert(photo_items[i]['date'])
            new_value = photo_params.get(likes_count, [])
            new_value.append({'likes_count': likes_count,
                              'add_name': time_warp,
                              'url_picture': url_download,
                              'size': picture_size})
            photo_params[likes_count] = new_value
        return photo_params

    def _sort_info(self):
        """Получение словаря с параметрами фотографий и списка в JSON для выгрузки"""
        json_list = []
        sorted_dict = {}
        picture_dict = self._get_logs_only()
        counter = 0
        for elem in picture_dict.keys():
            for value in picture_dict[elem]:
                if len(picture_dict[elem]) == 1:
                    file_name = f'{value["likes_count"]}.jpeg'
                else:
                    file_name = f'{value["likes_count"]} {value["add_name"]}.jpeg'
                json_list.append({'file name': file_name, 'size': value["size"]})
                if value["likes_count"] == 0:
                    sorted_dict[file_name] = picture_dict[elem][counter]['url_picture']
                    counter += 1
                else:
                    sorted_dict[file_name] = picture_dict[elem][0]['url_picture']
        return json_list, sorted_dict


class Yandex:
    def __init__(self, folder_name, token_list, num=5):
        """Получение основных параметров для загрузки фото на Яндекс-диск"""
        self.token = token_list[0]
        self.added_files_num = num
        self.url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
        self.headers = {'Authorization': self.token}
        self.folder = self._create_folder(folder_name)

    def _create_folder(self, folder_name):
        """Создание папки на Яндекс-диске для загрузки фото"""
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {'path': folder_name}
        if requests.get(url, headers=self.headers, params=params).status_code != 200:
            requests.put(url, headers=self.headers, params=params)
            print(f'\nПапка {folder_name} успешно создана!\n')
        else:
            print(f'\nПапка {folder_name} уже существует !!!файлы с одинаковыми именами не будут скопированы!!!\n')
        return folder_name

    def _in_folder(self, folder_name):
        """Получение ссылки для загрузки фото на Яндекс-диск"""
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {'path': folder_name}
        resource = requests.get(url, headers=self.headers, params=params).json()['_embedded']['items']
        in_folder_list = []
        for elem in resource:
            in_folder_list.append(elem['name'])
        return in_folder_list

    def create_copy(self, dict_files):
        """Загрузка фото на Яндекс-диск"""
        files_in_folder = self._in_folder(self.folder)
        copy_counter = 0
        for key, i in zip(dict_files.keys(), tqdm(range(self.added_files_num))):
            if copy_counter < self.added_files_num:
                if key not in files_in_folder:
                    params = {'path': f'{self.folder}/{key}',
                              'url': dict_files[key],
                              'overwrite': 'false'}
                    requests.post(self.url, headers=self.headers, params=params)
                    copy_counter += 1
                else:
                    print(f'Осторожно, файл {key} уже существует!')
            else:
                break

        print(f'\nЗапрос завершен, новых файлов скопировано: {copy_counter}'
              f'\nВсего файлов в исходном альбоме VK: {len(dict_files)}')


if __name__ == '__main__':

    VK_TOKEN = 'Vk_TOKEN.txt'  # токен и id доступа хранятся в файле на отдельных строках
    YA_TOKEN = 'Ya_TOKEN.txt'  # токен Яндекс-диска

    my_VK = VkParams(get_token_id(VK_TOKEN))  # Получение JSON с информацией о фото

    with open('VK_photo.json', 'w') as outfile:  # Сохранение в файл VK_photo.json
        json.dump(my_VK.json, outfile)

    # Создаем экземпляр класса Yandex с параметрами: "Имя папки", "Токен" и количество скачиваемых файлов
    my_yandex = Yandex('VK photo copies', get_token_id(YA_TOKEN), 5)
    my_yandex.create_copy(my_VK.export_dict)  # Метод create_copy для копирования фотографий с VK на Яндекс-диск
