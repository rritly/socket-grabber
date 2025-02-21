import asyncio
from contextlib import asynccontextmanager
from typing import Tuple, Any, Literal, AsyncGenerator
from bitstring import Bits
from struct import pack, unpack


class Parser:
    def __init__(self, config: dict, db_name: Literal["db_READ", "db_WRITE"]) -> None:
        """
        Парсинг конфига и данных из контроллера. При передаче - кодирование в байты

        :param config: Конфигурация контроллера, структура блоков данных
        :param db_name: Имя блока данных
        """
        self._bool_names: dict = {}
        self._usint_names: dict = {}
        self._int_names: dict = {}
        self._dint_names: dict = {}
        self._real_names: dict = {}
        self._array_of_real_names: dict = {}
        self.out_dict: dict = {}
        self._lookup = [format(b, "08b")[::-1] for b in range(256)]
        # Из конфига парсит имена, типы данных и адреса.
        for k in config[db_name].splitlines():
            kk = k.split(" ")
            byte_num, bit_num = map(int, kk[0].split("."))
            match kk[2]:
                case "BOOL":
                    self._bool_names[kk[1]] = byte_num * 8 + bit_num
                    self.out_dict[kk[1]] = False
                case "USINT":
                    self._usint_names[kk[1]] = byte_num * 8 + bit_num
                    self.out_dict[kk[1]] = 0
                case "INT":
                    self._int_names[kk[1]] = byte_num * 8 + bit_num
                    self.out_dict[kk[1]] = 0
                case "DINT":
                    self._dint_names[kk[1]] = byte_num * 8 + bit_num
                    self.out_dict[kk[1]] = 0
                case "REAL":
                    self._real_names[kk[1]] = byte_num * 8 + bit_num
                    self.out_dict[kk[1]] = 0.00
                case "ARRAY_OF_REAL":
                    self.out_dict[kk[1]] = []
                    self._array_of_real_names[kk[1]] = (
                        (byte_num * 8 + bit_num),  # Стартовый битовый номер
                        int(kk[3]),  # Длина массива
                    )

    @staticmethod
    def decode_sign(bits: str, len_b: int) -> int | None:
        positive: str = ""
        build_neg: str = ""
        negative: str = ""
        # Биты до 7го и после переворачиваются, склеиваются и конвертируются в целое со знаком
        if bits[7] == "0":
            if len_b == 16:
                positive = (bits[8:] + bits[:7])[::-1]
            if len_b == 32:
                positive = (bits[-8:] + bits[16:24] + bits[8:16] + bits[:7])[::-1]
            return int(positive, 2)
        # Если число отрицательное, применяется NOT. Меняется знак и вычитается 1.
        elif bits[7] == "1":
            for bit in bits:
                if bit == "0":
                    build_neg += "1"
                if bit == "1":
                    build_neg += "0"
            if len_b == 16:
                negative = (build_neg[8:] + build_neg[:7])[::-1]
            elif len_b == 32:
                negative = (build_neg[-8:] + build_neg[16:24] + build_neg[8:16] + build_neg[:7])[::-1]
            return -1 * int(negative, 2) - 1
        else:
            return None

    @staticmethod
    def encode_sign(num: int, len_b: int) -> str | None:
        data = Bits(int=num, length=len_b)
        if len_b == 16:
            out_bits = (data.bin[8:] + data.bin[0] + data.bin[1:8])[::-1]
            return out_bits
        elif len_b == 32:
            out_bits = (data.bin[-8:] + data.bin[16:24] + data.bin[8:16] + data.bin[0] + data.bin[1:8])[::-1]
            return out_bits
        else:
            return None

    # Преобразует биты в байты. Каждый байт переворачивается.
    @staticmethod
    def bit_to_byte(bit_string: str) -> bytes:
        out_byte = b""
        for i in range(0, len(bit_string), 8):
            integer_value = int(bit_string[i : i + 8][::-1], 2)
            out_byte += bytes([integer_value])
        return out_byte

    def read_from_plc(
        self, serial_bits: str
    ) -> dict[Literal["READ", "WRITE"], dict[str, bool | int | float | list]]:
        """

        :param serial_bits: Строка бит
        :return: Словарь с принятыми данными
        """
        # Извлекает тип bool и кладет в словарь
        for (key, val,) in self._bool_names.items():
            self.out_dict[key] = serial_bits[val] == "1"
        # Извлекает тип usint и кладет в словарь
        for key, val in self._usint_names.items():
            self.out_dict[key] = int(serial_bits[val : 8 + val][::-1], 2)
        # Извлекает тип int и кладет в словарь
        for key, val in self._int_names.items():
            self.out_dict[key] = self.decode_sign(bits=serial_bits[val : 16 + val], len_b=16)
        # Извлекает тип dint и кладет в словарь
        for key, val in self._dint_names.items():
            self.out_dict[key] = self.decode_sign(bits=serial_bits[val : 32 + val], len_b=32)
        # Извлекает тип real и кладет в словарь
        for key, val in self._real_names.items():
            dec_real = int(serial_bits[val : 32 + val][::-1], 2)
            self.out_dict[key] = unpack("<f", pack(">I", dec_real))[0]
        # Извлекает тип array_of_real и кладет в словарь
        for key, (addr, lenv) in self._array_of_real_names.items():
            self.out_dict[key] = []
            for i in range(lenv):
                dec_arr_real = int(serial_bits[i * 32 + addr : 32 + i * 32 + addr][::-1], 2)
                float_repr = unpack("<f", pack(">I", dec_arr_real))[0]
                self.out_dict[key].append(float_repr)
        return {
            "READ": {
                k: v
                for k, v in self.out_dict.items()
                if not k.startswith("copyDbWrite")
            },
            "WRITE": {
                k[12:]: v
                for k, v in self.out_dict.items()
                if k.startswith("copyDbWrite")
            },
        }

    def write_to_plc(self, in_dict: dict) -> bytes:
        """
        Принимает полный словарь для записи.

        :param in_dict: Полный словарь для записи в блок db_WRITE
        :return: Байты для передачи по сокету
        """
        serial_bits: list = []
        # Для bool
        for (key, val,) in self._bool_names.items():
            if key in in_dict:
                if val >= len(serial_bits,):
                  # Создает новые элементы списка если их нехватает
                    serial_bits.extend(["0"] * (val + 1 - len(serial_bits)))
                serial_bits[val] = "1" if in_dict[key] else "0"
            else:
                raise ValueError(f"Ключа {key} нет во входном словаре")
        # Для us_int
        for key, val in self._usint_names.items():
            if key in in_dict:
                b = bin(in_dict[key])[2:].zfill(8)
                b1 = b[::-1]
                if val >= len(serial_bits):
                    serial_bits.extend(["0"] * (val + 1 - len(serial_bits)))
                serial_bits.extend(["0"] * 7)
                for i in range(8):
                    serial_bits[val + i] = b1[i]
            else:
                raise ValueError(f"Ключа {key} нет во входном словаре")
        # Для int
        for key, val in self._int_names.items():
            if key in in_dict:
                enc_int = self.encode_sign(in_dict[key], 16)
                if enc_int is not None:
                    if val >= len(serial_bits):
                        serial_bits.extend(["0"] * (val + 1 - len(serial_bits)))
                    serial_bits.extend(["0"] * 15)
                    for i in range(16):
                        serial_bits[val + i] = enc_int[i]
                else:
                    raise ValueError(f"encode_sign() (int) вернул None")
            else:
                raise ValueError(f"Ключа {key} нет во входном словаре")
        # Для real
        for key, val in self._real_names.items():
            if key in in_dict:
                b_arr = pack(">f", round(in_dict[key], 5))
                bits = "".join(self._lookup[byte] for byte in b_arr)
                if val >= len(serial_bits):
                    serial_bits.extend(["0"] * (val + 1 - len(serial_bits)))
                serial_bits.extend(["0"] * 31)
                for i in range(32):
                    serial_bits[val + i] = bits[i]
            else:
                raise ValueError(f"Ключа {key} нет во входном словаре")
        # Для duble_int
        for key, val in self._dint_names.items():
            if key in in_dict:
                enc_duble_int = self.encode_sign(in_dict[key], 32)
                if enc_duble_int is not None:
                    if val >= len(serial_bits):
                        serial_bits.extend(["0"] * (val + 1 - len(serial_bits)))
                    serial_bits.extend(["0"] * 31)
                    for i in range(32):
                        serial_bits[val + i] = enc_duble_int[i]
                else:
                    raise ValueError(f"encode_sign() (duble_int) вернул None")
            else:
                raise ValueError(f"Ключа {key} нет во входном словаре")
        return self.bit_to_byte("".join(serial_bits))


class ControllerHandler:
    def __init__(self, config: Any,) -> None:
        """

        :param config: Конфигурация контроллера
        """
        self.device_config = dict(config)
        self.read_parser = Parser(self.device_config, "db_READ")
        self.write_parser = Parser(self.device_config, "db_WRITE")
        self.port_read = self.device_config["port_read"]
        self.port_write = self.device_config["port_write"]
        self.device_ip = self.device_config["ip"]
        self.lookup = [format(b, "08b")[::-1] for b in range(256)]

    @asynccontextmanager
    async def _init_conn_receive(
        self,
    ) -> AsyncGenerator[Tuple[asyncio.StreamReader, asyncio.StreamWriter], None]:
        """"""
        reader, writer = await asyncio.open_connection(self.device_ip, self.port_read)
        try:
            yield reader, writer
        finally:
            writer.close()
            await writer.wait_closed()

    @asynccontextmanager
    async def _init_conn_transmit(
        self,
    ) -> AsyncGenerator[Tuple[asyncio.StreamReader, asyncio.StreamWriter], None]:
        """"""
        reader, writer = await asyncio.open_connection(self.device_ip, self.port_write)
        try:
            yield reader, writer
        finally:
            writer.close()
            await writer.wait_closed()

    async def receive(self) -> dict:
        try:
            async with self._init_conn_receive() as (reader, writer):
                msg = await reader.read(1024)
            if not msg:
                raise ConnectionResetError("Соединение закрыто сервером")
            msg_bits = "".join(self.lookup[byte] for byte in msg)
            return self.read_parser.read_from_plc(msg_bits)
        except (ConnectionResetError, BrokenPipeError) as e:
            raise ConnectionError(f"Потеря коннекта {self.device_ip}:{self.port_read}") from e
        except (ConnectionRefusedError, OSError) as e:
            raise OSError(f"Сервер {self.device_ip}:{self.port_read} недоступен") from e

    async def transmit(self, in_dict: dict) -> None:
        try:
            trv = self.write_parser.write_to_plc(in_dict)
            async with self._init_conn_transmit() as (reader, writer):
                writer.write(trv)
                await writer.drain()
                await asyncio.sleep(0.05)
        except (ConnectionResetError, BrokenPipeError) as e:
            raise ConnectionError(f"Потеря коннекта {self.device_ip}:{self.port_write}") from e
        except (ConnectionRefusedError, OSError) as e:
            raise OSError(f"Сервер {self.device_ip}:{self.port_write} недоступен",) from e

