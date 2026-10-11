"""
Gera firmware.merged.bin (bootloader + tabela de particoes + aplicacao).

O Wokwi carrega a imagem completa da flash, nao so a aplicacao. Sem esse
merge a simulacao fica em boot loop. Roda automaticamente apos cada build.
"""
Import("env")  # noqa: F821  (injetado pelo PlatformIO)


def merge_bin(source, target, env):
    app = env.subst("$BUILD_DIR/firmware.bin")
    merged = env.subst("$BUILD_DIR/firmware.merged.bin")
    board = env.BoardConfig()

    images = []
    for item in env.Flatten(env.get("FLASH_EXTRA_IMAGES", [])):
        images.append(str(item))
    images += [env.subst("$ESP32_APP_OFFSET"), app]

    cmd = [
        "--chip", board.get("build.mcu", "esp32"),
        "merge_bin", "-o", merged,
        "--flash_mode", board.get("build.flash_mode", "dio"),
        "--flash_freq", board.get("build.f_flash", "40000000L").replace("000000L", "m"),
        "--flash_size", board.get("upload.flash_size", "4MB"),
    ] + images

    env.Execute(" ".join(['"$PYTHONEXE" "$OBJCOPY"'] + ['"%s"' % c for c in cmd]))
    print("[merge_bin] gerado: %s" % merged)


env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", merge_bin)  # noqa: F821
