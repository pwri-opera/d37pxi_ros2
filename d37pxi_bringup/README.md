# d37pxi_bringup

## MC Control GUI

[`script/mc_control_gui.py`](script/mc_control_gui.py) は、D37PXI の MC（マシンコントロール）、ブレード、走行の操作要求を ROS 2 トピックへ送信する GUI です。以下では、提示された画面写真の上から下の順に各ボタンを説明します。

### 起動

`d37pxi_bringup` をビルドし、ワークスペースの `install/setup.bash` を読み込んだ端末で実行します。

```bash
ros2 run d37pxi_bringup mc_control_gui.py
```

Python の Tkinter、`rclpy`、`std_msgs`、`com3_msgs` が必要です。実機への操作には、対応するドライバや MC Wrapper も起動している必要があります。GUI は操作要求を送信するもので、実機の現在状態や操作の完了を表示する機能はありません。

### 非常停止（画面最上部）

| ボタン | 説明 |
| --- | --- |
| **非常停止**（赤色） | エンジン停止のための非常停止要求を送信します。要求は自動解除されず、ドライバ側で次の指令まで保持されます。 |
| **非常停止解除** | 非常停止要求を解除します。エンジン始動指令は送信しません。 |

### MC・ブレード操作（画面中央）

| 項目 | ボタン | 説明・操作方法 |
| --- | --- | --- |
| Horn | ON | ホーンの作動要求を送信します。クリックすると `true` を送り、約 0.2 秒後に `false` を送ります。 |
| Lift Blade | ON | ブレード上昇のスイッチ要求を送信します。クリックすると `true` を送り、約 0.2 秒後に `false` を送ります。 |
| Initialize Blade | ON | MC Wrapper にブレードの初期化を要求します。初期化ではブレード各軸を動かすシーケンスが実行されます。 |
| Enable MC | ON / OFF | MC の有効化／無効化を要求します。クリック時に ON は `true`、OFF は `false` を送ります。 |
| Back Grading | ON / OFF | 後進時の整地機能（Back Grading）の有効化／無効化を要求します。 |
| Reset MC | Reset MC | MC の再有効化処理を要求します。ドライバは MC の推定状態を OFF として切替パルスを送り、ON として扱います。同時に Back Grading の要求・推定状態を OFF に戻します。**実機の MC が OFF であることを確認してから使用します。** GUI 自体ではその確認を行いません。 |
| Cutfill Level | UP / DOWN | 切土・盛土レベルを上げる／下げる要求を、クリックごとに送ります。変更量は GUI では指定しません。 |
| Blade Effort | Up / Down | ブレードのリフト軸へ短時間の指令を送ります。Up は `+127`、Down は `-126` を約 20 ms 間隔で 4 回送信し、最後に `0` を送ります。長押しによる連続操作ではありません。 |
| Blade Angle | Left / Right | マウスの左ボタンで**押している間**、アングル軸へ Left は `-1`、Right は `+1` を約 100 ms 間隔で送ります。離すと、その軸の指令を `0` に戻します。 |
| Blade Tilt | -120 / +120 | マウスの左ボタンで**押している間**、チルト軸へ表示どおり `-120`／`+120` を約 100 ms 間隔で送ります。離すと、その軸の指令を `0` に戻します。数値は指令値であり、角度（度）ではありません。 |

`Lift Blade` はスイッチ要求、`Blade Effort` はリフト軸への数値指令です。送信先と操作方式が異なります。

### Track Command（画面下部）

| 項目・ボタン | 説明・操作方法 |
| --- | --- |
| Decel (0 - 170) | デセル指令値を整数 `0`～`170` で入力します。初期値は `0`、空欄も `0` として扱います。速度の単位付き指定ではありません。0 で最大速度 160~170 付近で停止します |
| NFR | 走行方向を選択します。`0`：N（中立）、`1`：F（前進）、`2`：R（後進）。初期値は `0` です。 |
| Publish | 現在の Decel と NFR の連続送信を開始します。約 100 ms 間隔で入力値を読み直すため、送信中の入力変更も次回の送信に反映されます。 |
| Stop | 走行指令の連続送信を終了し、`decel=0, nfr=0, turn=0` の中立指令を 1 回送ります。非常停止（エンジン停止）の操作とは別です。 |

旋回指令 `turn` は常に `0` です。この画面には旋回を指定する操作はありません。

操作例：Decel を入力し、NFR を選択して **Publish** を押します。連続送信を終了するときは **Stop** を押します。

### ウィンドウを閉じたとき

タイトルバーの閉じるボタンでは、操作中のチルト・アングル軸の指令を `0` に戻し、走行指令の連続送信を終了して中立指令を送信した後に GUI を終了します。非常停止解除や MC の OFF 要求は送信しません。

### 送信トピック

以下は、名前空間やリマップを追加せずに起動した場合のトピック名です。

| 操作 | トピック | メッセージ型 |
| --- | --- | --- |
| 非常停止／解除 | `/d37pxi/emg_stop` | `std_msgs/msg/Bool` |
| Horn | `/d37pxi/horn` | `std_msgs/msg/Bool` |
| Lift Blade | `/d37pxi/mc/lift_blade` | `std_msgs/msg/Bool` |
| Initialize Blade | `/d37pxi/mc/initialize_blade` | `std_msgs/msg/Bool` |
| Enable MC | `/d37pxi/mc/enable_mc` | `std_msgs/msg/Bool` |
| Back Grading | `/d37pxi/mc/enable_back_grading` | `std_msgs/msg/Bool` |
| Reset MC | `/d37pxi/mc/reset_mc` | `std_msgs/msg/Empty` |
| Cutfill Level UP / DOWN | `/d37pxi/mc/cutfill_level_up` / `/d37pxi/mc/cutfill_level_down` | `std_msgs/msg/Bool` |
| Blade Effort / Angle / Tilt | `/d37pxi/blade_cmd` | `com3_msgs/msg/JointCmd` |
| Track Command | `/d37pxi/track_cmd` | `com3_msgs/msg/JointCmd` |
