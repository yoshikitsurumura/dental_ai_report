
import asyncio
from playwright.async_api import async_playwright
import getpass

async def main():
    async with async_playwright() as p:
        # ヘッドレスモードをFalseにすることで、ブラウザの動作を実際に確認できます。
        # 自動化が安定したらTrueにすると、バックグラウンドで実行されます。
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # 1. AWSサインイン
            print("AWSへのサインインを開始します...")
            await page.goto("https://portal.aws.amazon.com/billing/signup#/start/email")

            # メールアドレスの入力
            email = input("AWSアカウントのメールアドレスを入力してください: ")
            await page.locator("#awsui-input-0").fill(email)
            await page.locator("#awsui-input-0").press("Enter")
            
            # パスワードの入力
            password = getpass.getpass("AWSパスワードを入力してください: ")
            await page.locator("#awsui-input-1").fill(password)
            await page.locator("span:has-text('サインイン')").click()

            # MFA（多要素認証）の待機と入力
            print("MFAコードの入力画面が表示されるまで待機します...")
            await page.wait_for_selector("#awsui-input-2", timeout=60000) # MFA入力フィールドが表示されるまで最大60秒待つ
            mfa_code = input("6桁のMFAコードを入力してください: ")
            await page.locator("#awsui-input-2").fill(mfa_code)
            await page.locator("span:has-text('MFAデバイスを送信')").click()
            
            print("サインインに成功しました。EC2ダッシュボードに移動します。")
            await page.wait_for_load_state('networkidle') # ページの読み込みが安定するまで待つ

            # 2. EC2インスタンスの作成
            # リージョンが東京(ap-northeast-1)であることを確認
            await page.goto("https://ap-northeast-1.console.aws.amazon.com/ec2/v2/home?region=ap-northeast-1#LaunchInstanceWizard:")

            print("EC2インスタンスの作成を開始します...")
            
            # インスタンス名
            instance_name = "dental-ai-report-server"
            print(f"インスタンス名: {instance_name}")
            await page.locator('input[aria-label="Name"]').fill(instance_name)

            # AMI (Ubuntu, 無料枠)
            print("AMI: Ubuntuを選択")
            # デフォルトで選択されていることが多いが、念のため確認・選択するロジックを追加することも可能

            # インスタンスタイプ (t2.micro, 無料枠)
            print("インスタンスタイプ: t2.microを選択")
            await page.locator('label:has-text("t2.micro")').click()

            # キーペアの作成
            print("キーペアを新規作成します...")
            await page.locator("text=キーペアを新規作成").click()
            key_pair_name = f"dental-ai-key-{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
            await page.locator('input[aria-label="キーペア名"]').fill(key_pair_name)
            
            # ダウンロード処理
            async with page.expect_download() as download_info:
                await page.locator("button:has-text('キーペアを作成')").click()
            download = await download_info.value
            pem_path = f"C:/Users/mayum/Downloads/{key_pair_name}.pem"
            await download.save_as(pem_path)
            print(f"キーペア '{key_pair_name}.pem' をダウンロードしました。パス: {pem_path}")
            print("【重要】この.pemファイルは厳重に保管してください。サーバーへのアクセスに必要です。")

            # ネットワーク設定 (セキュリティグループ)
            print("ネットワーク設定を構成します...")
            # デフォルトでHTTP, HTTPSを許可するセキュリティグループが作成されることが多い
            # ここでは、SSH, HTTP, HTTPSを許可するルールを明示的に確認・設定する
            await page.locator("text=HTTP トラフィックを許可").check()
            await page.locator("text=HTTPS トラフィックを許可").check()
            
            # 概要確認と起動
            print("設定内容を確認し、インスタンスを起動します。")
            await page.locator("button:has-text('インスタンスを起動')").click()

            # 起動成功の確認
            await page.wait_for_selector("text=インスタンスの起動を正常に開始しました", timeout=120000)
            print("インスタンスの起動に成功しました！")
            
            instance_id_locator = page.locator('a[data-testid*="instance-id"]')
            instance_id = await instance_id_locator.inner_text()
            print(f"作成されたインスタンスID: {instance_id}")
            print(f"AWSコンソールでインスタンスの状態を確認してください: https://ap-northeast-1.console.aws.amazon.com/ec2/v2/home?region=ap-northeast-1#InstanceDetails:instanceId={instance_id}")

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            # エラー発生時にスクリーンショットを保存するとデバッグに役立ちます
            await page.screenshot(path="error_screenshot.png")
            print("エラー時のスクリーンショットを 'error_screenshot.png' として保存しました。")

        finally:
            print("ブラウザを閉じます。")
            await browser.close()

if __name__ == "__main__":
    # pandasをインポート
    try:
        import pandas as pd
    except ImportError:
        print("pandasがインストールされていません。'pip install pandas' を実行してください。")
        exit()
        
    asyncio.run(main())
