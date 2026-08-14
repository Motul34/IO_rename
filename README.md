# UR IO & Node Editor

Universal Robots (UR) ロボットの `.installation` ファイルと `.urp` ファイルを編集するデスクトップアプリケーションです。

## 機能

- **IO 名称の編集**: Digital / Tool / Analog / GP Boolean / GP Int / GP Float の入出力名を編集
- **ノード名称の編集**: Folder / Assignment / Comment / Timer / Waypoint のノード名を編集
- **プログラムツリー表示**: URP ファイルのプログラム構造をツリー形式で可視化
- **GP アドレスの自動連番**: GP レジスタのアドレスを入力すると他の行も自動連番

## 必要環境

- Python 3.14 以上
- [uv](https://docs.astral.sh/uv/) パッケージマネージャー

## セットアップ

```bash
# 依存パッケージのインストール
uv sync
```

## 使用方法

```bash
# アプリケーションの起動
uv run python main.py
```

### キーボードショートカット

| ショートカット | 機能 |
|--------------|------|
| `Ctrl+O` | ファイルを開く |
| `Ctrl+S` | 上書き保存 |
| `Ctrl+Shift+S` | 名前を付けて保存 |

### 操作手順

1. **ファイル → ファイルを開く** または **フォルダを開く** で対象ファイルを選択
2. 各タブで IO 名称やノード名を編集
3. **ファイル → 上書き保存** で変更を保存

## ビルド（EXE 作成）

```bash
build.bat
```

`dist/IO_Editor.exe` が生成されます。

## プロジェクト構成

```
IO_rename/
├── main.py           # メインウィンドウ・UI
├── io_manager.py     # .installation ファイルの読み書き
├── urp_manager.py    # .urp ファイルの読み書き
├── xml_resolver.py   # XML 要素の名前解決・式パース
├── tree_builder.py   # プログラムツリーの構築
├── build.bat         # PyInstaller ビルドスクリプト
├── IO_Editor.spec    # PyInstaller 設定
├── icon.ico          # アプリケーションアイコン
└── pyproject.toml    # プロジェクト設定
```
