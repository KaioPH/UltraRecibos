
"""
Impede que o Ultra Recibos seja aberto duas vezes ao mesmo tempo
no mesmo usuário do Windows.

- Windows: "mutex" nomeado do sistema (liberado automaticamente pelo
  Windows quando o programa fecha, inclusive se travar ou for encerrado).
- Outros sistemas (apenas desenvolvimento/testes): trava de arquivo.

Se já houver uma cópia aberta, a janela existente é trazida para a frente.
"""

import hashlib
import os
import sys

from caminhos import PASTA_DADOS


ERROR_ALREADY_EXISTS = 183
TITULO_JANELA = "Ultra Recibos"

_trava = None  # mantém o mutex/arquivo aberto enquanto o programa roda


def _identificador():
    # Um identificador por pasta de dados (testes não interferem no uso real)
    resumo = hashlib.sha1(str(PASTA_DADOS.resolve()).lower().encode("utf-8")).hexdigest()[:12]
    return f"UltraRecibos_InstanciaUnica_{resumo}"


def adquirir():
    """
    Retorna True se esta é a única cópia aberta.
    """

    if _trava is not None:
        return True

    if sys.platform.startswith("win"):
        return _adquirir_windows()

    return _adquirir_arquivo()


def _adquirir_windows():

    global _trava

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)

    # "Local\\" = válido somente para a sessão do usuário atual
    handle = kernel32.CreateMutexW(None, False, "Local\\" + _identificador())

    if not handle:
        # Não foi possível criar o mutex: não bloqueia o uso do programa
        return True

    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return False

    _trava = handle
    return True


def _adquirir_arquivo():

    global _trava

    import fcntl

    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    arquivo = open(PASTA_DADOS / ".instancia.lock", "w")

    try:
        fcntl.flock(arquivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        arquivo.close()
        return False

    _trava = arquivo
    return True


def liberar():
    """
    Libera a trava (usado nos testes; o sistema libera ao fechar).
    """

    global _trava

    if _trava is None:
        return

    if sys.platform.startswith("win"):
        import ctypes
        ctypes.WinDLL("kernel32").CloseHandle(_trava)
    else:
        _trava.close()

    _trava = None


def trazer_janela_existente():
    """
    Restaura e traz para a frente a janela principal já aberta (Windows).
    Retorna True se encontrou a janela.
    """

    if not sys.platform.startswith("win"):
        return False

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    encontradas = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def verificar(hwnd, _lparam):
        tamanho = user32.GetWindowTextLengthW(hwnd)
        if tamanho and user32.IsWindowVisible(hwnd):
            buffer = ctypes.create_unicode_buffer(tamanho + 1)
            user32.GetWindowTextW(hwnd, buffer, tamanho + 1)
            titulo = buffer.value
            # Janela principal: "Ultra Recibos 2.x.x" (não as Configurações)
            if titulo.startswith(TITULO_JANELA + " ") and titulo[len(TITULO_JANELA) + 1:][:1].isdigit():
                encontradas.append(hwnd)
        return True

    user32.EnumWindows(verificar, 0)

    if not encontradas:
        return False

    hwnd = encontradas[0]
    SW_RESTORE = 9
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    return True


def avisar_ja_aberto():
    """
    Mostra o aviso e traz a janela existente para a frente.
    """

    if trazer_janela_existente():
        return

    import tkinter
    from tkinter import messagebox

    raiz = tkinter.Tk()
    raiz.withdraw()
    messagebox.showinfo(
        "Ultra Recibos",
        "O Ultra Recibos já está aberto neste computador.\n\n"
        "Procure a janela na barra de tarefas.",
        parent=raiz
    )
    raiz.destroy()


if __name__ == "__main__":
    print("Única cópia:", adquirir())
    os.system("pause" if sys.platform.startswith("win") else "true")
