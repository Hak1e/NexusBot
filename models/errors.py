class DataBaseFetchError(Exception):
    """Возникает, когда параметр не был найден в базе данных"""
    def __init__(self, message="Ошибка при извлечении данных из базы данных"):
        super().__init__(message)
