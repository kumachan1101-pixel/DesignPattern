import pyautogui
import pyperclip
import time

# 処理対象のテキストファイルパスを指定
target_text_path = r"C:\Users\kumac\OneDrive\デスクトップ\antigravity\DesignPattern\kindle\design-patterns\script\step_word.txt"  # ここに処理したいテキストファイルのパスを指定してください

print("開始：指定したテキストの内容を1行ずつ貼り付けます。")
time.sleep(5)

# 処理対象のテキストファイルを読み込み、各行を処理する
try:
    with open(target_text_path, encoding='utf-8') as target_f:
        for line in target_f:
            line = line.strip()  # 行末の改行コードなどを削除
            if line:  # 空行はスキップ

                # 現在の行をクリップボードにコピーして貼り付け、Enterを押す
                pyperclip.copy(line)
                pyautogui.hotkey('ctrl', 'v')  # Macなら 'command' に変更してください
                time.sleep(5)
                pyautogui.press('enter')

                print(f"固定テキストと行 '{line}' を貼り付けました。待ちます。")
                time.sleep(60)  # 必要に応じて待ち時間を調整

except FileNotFoundError:
    print(f"エラー：処理対象のテキストファイルが見つかりませんでした: {target_text_path}")
except Exception as e:
    print(f"エラーが発生しました: {e}")

print("すべての行の貼り付けが完了しました。")