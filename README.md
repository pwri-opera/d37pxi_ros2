# d37pxi_ros2
OPERA 対応ブルドーザ d37pxi-24 の土木研究所公開 ROS2 パッケージ群

## 概説
- 国立研究開発法人土木研究所が公開する OPERA（Open Platform for Eathwork with Robotics Autonomy）対応のブルドーザ d37pxi-24 用の ROS2 パッケージ群
- 本パッケージに含まれる各 launch ファイルを起動することで，実機やシミュレータを動作させるのに必要なROSノード群が起動
- 動作環境: ROS2 Humble Hawksbil + Ubuntu 22.04 LTS

## 含有するサブパッケージ

| サブパッケージ | 内容 |
| --- | --- |
| `d37pxi_description` | URDF/Xacro、メッシュ、モデル表示用 launch・RViz 設定 |
| `d37pxi_navigation` | Nav2 周りの設定 |
| `d37pxi_bringup` | 実機向けのモデル表示・自己位置推定・Nav2 の一括起動 |
| `d37pxi_unity` | OperaSim-AGX 用のモデル表示・自己位置推定・Nav2 の一括起動 (OperaSim-PhysX は現状(2026/9/17 現在)ブルドーザは未実装) |
| `d37pxi_control` | TBD (ブレード周りのコントローラを実装する可能性有り) |

## インストール・ビルド

- 以下は新規ワークスペース `~/ros2_ws` を作成する例
- 既存のワークスペースを使う場合はパスを読み替えること

### 1. 依存関係のインストール

- 事前準備：ROS 2 Humble、Git、C++ビルド環境が導入済みであること
- 現在はパッケージの実行時依存の宣言に不足があるため、以下の通り表示・自己位置推定・Nav2 に必要なパッケージを明示してインストールすること

```bash
source /opt/ros/humble/setup.bash
sudo apt update
sudo apt install python3-colcon-common-extensions python3-rosdep2 \
  ros-humble-xacro ros-humble-rviz2 ros-humble-robot-state-publisher \
  ros-humble-joint-state-publisher ros-humble-joint-state-publisher-gui \
  ros-humble-navigation2 ros-humble-nav2-bringup \
  ros-humble-robot-localization ros-humble-tf-transformations
```

### 2. ワークスペースの作成とソースの取得

- 以下のパッケージが必要

| 外部パッケージ | 取得元 | 本リポジトリとの関係 |
| --- | --- | --- |
| `com3_msgs` | [com3_ros](https://github.com/pwri-opera/com3_ros) | `d37pxi_control` が依存を宣言。ワークスペース全体の rosdep 処理で参照 |
| `gnss_localizer_ros2` | [gnss_localizer_ros2](https://github.com/pwri-opera/gnss_localizer_ros2) | `d37pxi_navigation` が依存を宣言 |

以下通り clone を実施

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone https://github.com/pwri-opera/d37pxi_ros2.git
git clone https://github.com/pwri-opera/com3_ros.git
git clone https://github.com/pwri-opera/gnss_localizer_ros2.git
cd ~/ros2_ws
```

### 3. 依存関係の解決及びパッケージのビルド

rosdep を初めて使用する環境では、一度だけ初期化

```bash
sudo rosdep init
```
以下通りパッケージの依存を解決 + ビルド
```bash
cd ~/ros2_ws
rosdep update
rosdep install --from-paths src --ignore-src --rosdistro humble -y
colcon build --symlink-install
source install/setup.bash
```

## 用途別の起動方法

### 1. OperaSim-AGX
TBD
<!-- ```bash
ros2 launch d37pxi_unity d37pxi_standby_ekf.launch.py \
  common_prefix:=d37pxi use_rviz:=true
``` -->

### 2. 実機
TBD
<!-- ```bash
ros2 launch d37pxi_bringup d37pxi_standby_ekf.launch.py \
  common_prefix:=d37pxi use_rviz:=true
``` -->


## 主要な設定とインターフェース

### launch 引数
TBD

### 外部入力・出力
TBD

### 各種設定ファイル

| ファイル | 内容 |
| --- | --- |
| [navigation_mppi.yaml](d37pxi_navigation/params/navigation_mppi.yaml) | 実機・OperaSim-AGX の一括起動が使用する Nav2 設定。速度・車体形状・経路追従・コストマップなど |
| [d37pxi_ekf.yaml](d37pxi_navigation/config/d37pxi_ekf.yaml) | EKF のパラメータ設定 |
| [map.yaml](d37pxi_navigation/map/map.yaml) / [map_sim.yaml](d37pxi_navigation/map/map_sim.yaml) | 実機用 / OperaSim-AGX 用の地図画像・解像度・原点 |
| [d37pxi24.xacro](d37pxi_description/urdf/d37pxi24.xacro) | 車体・関節・フレームのモデル |


