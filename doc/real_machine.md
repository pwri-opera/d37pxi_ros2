# 実機でのシステム立ち上げ

 - 土研ブルドーザ D37PXi-24 の自動運転モードでの実機起動手順
 - ※操作順序も含め、現時点では確定した運用手順ではありません

[README に戻る](../README.md#用途別の起動方法リンク参照)

### 事前準備
- 実機の立ち会げ操作を実施する
  - ※自動運転モードでの立ち上げに必要な操作は、実際に機体を使用する際に説明する
  - 上記説明に従い機体を自動運転モードに設定し、設定が完了してから以降の手順に進むこと


### 起動方法

1. 車載PCに リモートデスクトップに接続 or ssh でログイン
2. 車載PCホームディレクトリ直下の ``setup_can.sh`` を実行
3. ターミナルを立ち上げ以下を実行
```bash
ros2 launch d37pxi_com3_ros com3_ros.launch.py
```
4. ※遠隔操作装置の 35/45 ボタンを押下 (実機の仕様時に説明)
5. 実機側の走行ロック，作業機ロックを解除するためには以下を実行
    - d37pxi_com3_ros（車載PCにあるROS2 パッケージ）直下の　setup_bull.sh　を実行

参考：`d37pxi_com3_ros/setup_bull.sh` は、次の設定を送信する。

| トピック | 型 | スクリプトの送信値 |
| --- | --- | --- |
| `/d37pxi/machine_setting_cmd/track_lock` | `std_msgs/msg/Bool` | `false`（走行ロック解除） |
| `/d37pxi/machine_setting_cmd/blade_lock` | `std_msgs/msg/Bool` | `false`（ブレードロック解除） |
| `/d37pxi/machine_setting_cmd/engine_rpm` | `std_msgs/msg/UInt8` | `0` |

- ロック解除を実施後，ブルドーザのエンジン回転数を調整する
  - ※ engine_rpm は エンジンの回転数 (最小0 ~ 最大256 : CANの指令値) である．ロック解除後，0以外の設定値を与える事

6. 自己位置推定・ナビゲーション関連ノードは以下により起動
```bash
ros2 launch d37pxi_bringup d37pxi_standby_ekf.launch.py \
  common_prefix:=d37pxi use_rviz:=true
```
- `common_prefix`：名前空間の接頭辞（既定値：`d37pxi`）
- `use_rviz`：RViz を起動する場合は `true`、起動しない場合は `false`
