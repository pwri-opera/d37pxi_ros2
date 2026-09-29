#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from std_msgs.msg import Empty
from com3_msgs.msg import JointCmd
import tkinter as tk
import time

class MachineSettingPublisher(Node):
    def __init__(self):
        super().__init__('machine_setting_publisher')

        # Publishers for individual Bool topics
        self.pubs = {
            'emg_stop': self.create_publisher(Bool, '/d37pxi/emg_stop', 10),
            'horn': self.create_publisher(Bool, 'd37pxi/horn', 10),
            'initialize_blade': self.create_publisher(
                Bool, 'd37pxi/mc/initialize_blade', 10),
            'enable_mc': self.create_publisher(Bool, 'd37pxi/mc/enable_mc', 10),
            'enable_back_grading': self.create_publisher(Bool, 'd37pxi/mc/enable_back_grading', 10),
            'lift_blade': self.create_publisher(Bool, 'd37pxi/mc/lift_blade', 10),
            'cutfill_level_up': self.create_publisher(Bool, 'd37pxi/mc/cutfill_level_up', 10),
            'cutfill_level_down': self.create_publisher(Bool, 'd37pxi/mc/cutfill_level_down', 10),
        }

        # Publisher for blade effort (JointCmd)
        self.pub_blade_effort = self.create_publisher(JointCmd, 'd37pxi/blade_cmd', 10)
        self.pub_track_effort = self.create_publisher(JointCmd, 'd37pxi/track_cmd', 10)
        self.pub_reset_mc = self.create_publisher(Empty, 'd37pxi/mc/reset_mc', 10)
        self.track_publish_active = False
        self.track_publish_period_ms = 100
        self.track_after_id = None
        self.blade_axes_publish_period_ms = 100
        self.blade_axes_after_id = None
        self.blade_axes_effort = {"tilt": 0.0, "angle": 0.0}

    def publish_bool(self, key, value):
        msg = Bool()
        msg.data = value
        self.pubs[key].publish(msg)
        self.get_logger().info(f"Published {key}: {value}")

        interval = 0.2
        time.sleep(interval)
        msg.data = False
        self.pubs[key].publish(msg)
        self.get_logger().info(f"Published {key}: {False}")

    def publish_cutfill_request(self, up):
        key = "cutfill_level_up" if up else "cutfill_level_down"
        msg = Bool()
        msg.data = True
        self.pubs[key].publish(msg)
        self.get_logger().info(f"Published {key} request: true")

    def publish_emg_stop(self, enabled):
        # This is a retained command, not a pulse: release only on explicit request.
        msg = Bool()
        msg.data = enabled
        self.pubs['emg_stop'].publish(msg)
        self.get_logger().info(f"Published emergency stop request: {enabled}")

    def publish_mc_request(self, enabled):
        msg = Bool()
        msg.data = enabled
        self.pubs['enable_mc'].publish(msg)
        self.get_logger().info(f"Published MC request: {enabled}")

    def initialize_blade(self):
        msg = Bool()
        msg.data = True
        self.pubs['initialize_blade'].publish(msg)
        self.get_logger().info("Published initialize blade request: true")

    def publish_back_grading_request(self, enabled):
        msg = Bool()
        msg.data = enabled
        self.pubs['enable_back_grading'].publish(msg)
        self.get_logger().info(f"Published Back Grading request: {enabled}")

    def reset_mc(self):
        self.pub_reset_mc.publish(Empty())
        self.get_logger().info("Published MC reset")

    def publish_track_effort(self, decel, nfr):
        msg = JointCmd()
        msg.joint_name = ['decel', 'nfr', 'turn']
        msg.control_type = 2
        msg.position = []
        msg.velocity = []
        msg.effort = [float(decel), float(nfr), 0.0]
        self.pub_track_effort.publish(msg)

    def publish_track_periodically(self, root, decel_var, nfr_var):
        if not self.track_publish_active:
            return

        decel = int(decel_var.get()) if decel_var.get() else 0
        nfr = max(0, min(2, int(nfr_var.get())))
        self.publish_track_effort(decel, nfr)
        self.track_after_id = root.after(
            self.track_publish_period_ms,
            lambda: self.publish_track_periodically(root, decel_var, nfr_var))

    def start_track_effort(self, root, decel_var, nfr_var):
        if self.track_publish_active:
            return

        self.track_publish_active = True
        self.get_logger().info(
            f"Started track command: decel={decel_var.get()}, nfr={nfr_var.get()}")
        self.publish_track_periodically(root, decel_var, nfr_var)

    def stop_track_effort(self, root):
        self.track_publish_active = False
        if self.track_after_id is not None:
            root.after_cancel(self.track_after_id)
            self.track_after_id = None

        self.publish_track_effort(0, 0)
        self.get_logger().info("Stopped track command and published neutral command")

    def validate_decel(self, value):
        return value == "" or (value.isdigit() and 0 <= int(value) <= 170)

    def publish_blade_axes_effort(self):
        msg = JointCmd()
        msg.joint_name = ['lift', 'tilt', 'angle']
        msg.control_type = 1
        msg.position = []
        msg.velocity = []
        msg.effort = [0.0, self.blade_axes_effort['tilt'], self.blade_axes_effort['angle']]
        self.pub_blade_effort.publish(msg)

    def publish_blade_axes_periodically(self, root):
        self.blade_axes_after_id = None
        if not any(self.blade_axes_effort.values()):
            return

        self.publish_blade_axes_effort()
        self.blade_axes_after_id = root.after(
            self.blade_axes_publish_period_ms,
            lambda: self.publish_blade_axes_periodically(root))

    def start_blade_axis_effort(self, root, axis, effort):
        self.blade_axes_effort[axis] = float(effort)
        if self.blade_axes_after_id is None:
            self.publish_blade_axes_periodically(root)
        else:
            self.publish_blade_axes_effort()
        self.get_logger().info(f"Started blade {axis} command: effort={effort}")

    def stop_blade_axis_effort(self, root, axis):
        if self.blade_axes_effort[axis] == 0.0:
            return

        self.blade_axes_effort[axis] = 0.0
        if not any(self.blade_axes_effort.values()) and self.blade_axes_after_id is not None:
            root.after_cancel(self.blade_axes_after_id)
            self.blade_axes_after_id = None

        self.publish_blade_axes_effort()
        self.get_logger().info(f"Stopped blade {axis} command")

    def publish_blade_effort(self, effort_value, repetitions=5, interval=0.02):
        msg = JointCmd()
        msg.joint_name = ['lift']
        msg.effort = [float(effort_value)]
        msg.position = [0.0]
        msg.velocity = [0.0]

        for _ in range(repetitions-1):
            self.pub_blade_effort.publish(msg)
            self.get_logger().info(f"Published JointCmd: lift effort {effort_value}")
            time.sleep(interval)

        # Return blade effort to 0 for safety
        msg.effort = [0.0]
        self.pub_blade_effort.publish(msg)
        self.get_logger().info(f"Published JointCmd: lift effort {0.0}")

    def up_trigger(self):
        self.publish_blade_effort(127.0) # max num

    def down_trigger(self):
        self.publish_blade_effort(-126.0) # min num

def main():
    rclpy.init()
    node = MachineSettingPublisher()

    root = tk.Tk()
    root.title("MC Control GUI")
    root.geometry("520x800")
    root.minsize(520, 800)

    button_font = ("Arial", 12)
    button_width = 15
    control_button_height = 1
    track_button_height = 2

    frame_emg_stop = tk.LabelFrame(root, text="非常停止（エンジン停止）")
    frame_emg_stop.pack(pady=10, padx=10, fill=tk.X)
    tk.Button(
        frame_emg_stop, text="非常停止", font=("Arial", 14, "bold"),
        bg="#c62828", fg="white", activebackground="#b71c1c",
        activeforeground="white", width=button_width, height=2,
        command=lambda: node.publish_emg_stop(True)).pack(side=tk.LEFT, padx=10, pady=5)
    tk.Button(
        frame_emg_stop, text="非常停止解除", font=button_font,
        width=button_width, height=control_button_height,
        command=lambda: node.publish_emg_stop(False)).pack(side=tk.LEFT, padx=10, pady=5)

    # Bool controls
    controls = [
        ("Horn", "horn"),
        ("Lift Blade", "lift_blade"),
    ]

    for label, key in controls:
        frame = tk.Frame(root)
        frame.pack(pady=3)
        tk.Label(frame, text=label, font=("Arial", 14)).pack(side=tk.LEFT, padx=10)
        tk.Button(frame, text="ON", font=button_font, width=button_width//2,
                  height=control_button_height,
                  command=lambda k=key: node.publish_bool(k, True)).pack(side=tk.LEFT, padx=5)
        # tk.Button(frame, text="OFF", font=button_font, width=button_width//2,
        #           height=control_button_height,
        #           command=lambda k=key: node.publish_bool(k, True)).pack(side=tk.LEFT, padx=5)

    frame_initialize_blade = tk.Frame(root)
    frame_initialize_blade.pack(pady=3)
    tk.Label(frame_initialize_blade, text="Initialize Blade", font=("Arial", 14)).pack(
        side=tk.LEFT, padx=10)
    tk.Button(
        frame_initialize_blade, text="ON", font=button_font,
        width=button_width//2, height=control_button_height,
        command=node.initialize_blade).pack(side=tk.LEFT, padx=5)

    # MC enable is a requested state, unlike the momentary controls above.
    frame_mc = tk.Frame(root)
    frame_mc.pack(pady=3)
    tk.Label(frame_mc, text="Enable MC", font=("Arial", 14)).pack(side=tk.LEFT, padx=10)
    tk.Button(frame_mc, text="ON", font=button_font, width=button_width//2,
              height=control_button_height,
              command=lambda: node.publish_mc_request(True)).pack(side=tk.LEFT, padx=5)
    tk.Button(frame_mc, text="OFF", font=button_font, width=button_width//2,
              height=control_button_height,
              command=lambda: node.publish_mc_request(False)).pack(side=tk.LEFT, padx=5)

    frame_back_grading = tk.Frame(root)
    frame_back_grading.pack(pady=3)
    tk.Label(frame_back_grading, text="Back Grading", font=("Arial", 14)).pack(
        side=tk.LEFT, padx=10)
    tk.Button(frame_back_grading, text="ON", font=button_font,
              width=button_width//2, height=control_button_height,
              command=lambda: node.publish_back_grading_request(True)).pack(
                  side=tk.LEFT, padx=5)
    tk.Button(frame_back_grading, text="OFF", font=button_font,
              width=button_width//2, height=control_button_height,
              command=lambda: node.publish_back_grading_request(False)).pack(
                  side=tk.LEFT, padx=5)

    frame_reset_mc = tk.Frame(root)
    frame_reset_mc.pack(pady=3)
    tk.Button(frame_reset_mc, text="Reset MC", font=button_font, width=button_width,
              height=control_button_height, command=node.reset_mc).pack(side=tk.LEFT, padx=5)


    # Cutfill Level
    frame_cutfill = tk.Frame(root)
    frame_cutfill.pack(pady=5)
    tk.Label(frame_cutfill, text="Cutfill Level", font=("Arial", 14)).pack(side=tk.LEFT, padx=10)
    tk.Button(frame_cutfill, text="UP", font=button_font, width=button_width//2,
              height=control_button_height,
              command=lambda: node.publish_cutfill_request(True)).pack(side=tk.LEFT, padx=5)
    tk.Button(frame_cutfill, text="DOWN", font=button_font, width=button_width//2,
              height=control_button_height,
              command=lambda: node.publish_cutfill_request(False)).pack(side=tk.LEFT, padx=5)

    # Blade Effort triggers
    frame_triggers = tk.Frame(root)
    frame_triggers.pack(pady=5)
    tk.Label(frame_triggers, text="Blade Effort", font=("Arial", 14)).pack(side=tk.LEFT, padx=10)
    tk.Button(frame_triggers, text="Up", font=button_font, width=button_width//2,
              height=control_button_height,
              command=node.up_trigger).pack(side=tk.LEFT, padx=5)
    tk.Button(frame_triggers, text="Down", font=button_font, width=button_width//2,
              height=control_button_height,
              command=node.down_trigger).pack(side=tk.LEFT, padx=5)

    # Blade angle is operated only while either button is held down.
    frame_angle = tk.Frame(root)
    frame_angle.pack(pady=3)
    tk.Label(frame_angle, text="Blade Angle", font=("Arial", 14)).pack(
        side=tk.LEFT, padx=10)
    angle_left_button = tk.Button(
        frame_angle, text="Left", font=button_font,
        width=button_width//2, height=control_button_height)
    angle_left_button.pack(side=tk.LEFT, padx=5)
    angle_right_button = tk.Button(
        frame_angle, text="Right", font=button_font,
        width=button_width//2, height=control_button_height)
    angle_right_button.pack(side=tk.LEFT, padx=5)

    angle_left_button.bind(
        "<ButtonPress-1>", lambda _event: node.start_blade_axis_effort(root, 'angle', -1.0))
    angle_left_button.bind(
        "<ButtonRelease-1>", lambda _event: node.stop_blade_axis_effort(root, 'angle'))
    angle_right_button.bind(
        "<ButtonPress-1>", lambda _event: node.start_blade_axis_effort(root, 'angle', 1.0))
    angle_right_button.bind(
        "<ButtonRelease-1>", lambda _event: node.stop_blade_axis_effort(root, 'angle'))

    # Blade tilt uses fixed effort while either button is held down.
    frame_tilt = tk.Frame(root)
    frame_tilt.pack(pady=3)
    tk.Label(frame_tilt, text="Blade Tilt", font=("Arial", 14)).pack(
        side=tk.LEFT, padx=10)
    for label, effort in (("-120", -120.0), ("+120", 120.0)):
        button = tk.Button(
            frame_tilt, text=label, font=button_font,
            width=button_width//2, height=control_button_height)
        button.pack(side=tk.LEFT, padx=5)
        button.bind(
            "<ButtonPress-1>",
            lambda _event, value=effort: node.start_blade_axis_effort(root, 'tilt', value))
        button.bind(
            "<ButtonRelease-1>", lambda _event: node.stop_blade_axis_effort(root, 'tilt'))

    # Track command controls. Only decel and nfr are user-selectable; turn is fixed at zero.
    decel_var = tk.StringVar(value="0")
    nfr_var = tk.IntVar(value=0)

    frame_track = tk.LabelFrame(root, text="Track Command")
    frame_track.pack(pady=10, padx=10, fill=tk.X)

    tk.Label(frame_track, text="Decel (0 - 170)", font=("Arial", 12)).grid(
        row=0, column=0, padx=5, pady=5, sticky=tk.W)

    decel_validation = root.register(node.validate_decel)
    tk.Entry(
        frame_track, textvariable=decel_var, width=8,
        validate="key", validatecommand=(decel_validation, "%P")).grid(
            row=0, column=1, padx=5, pady=5, sticky=tk.W)

    tk.Label(frame_track, text="NFR", font=("Arial", 12)).grid(
        row=1, column=0, padx=5, pady=5, sticky=tk.W)
    tk.OptionMenu(frame_track, nfr_var, 0, 1, 2).grid(
        row=1, column=1, padx=5, pady=5, sticky=tk.W)

    tk.Button(
        frame_track, text="Publish", font=button_font, width=button_width//2,
        height=track_button_height,
        command=lambda: node.start_track_effort(root, decel_var, nfr_var)).grid(
            row=2, column=0, padx=5, pady=5)
    tk.Button(
        frame_track, text="Stop", font=button_font, width=button_width//2,
        height=track_button_height,
        command=lambda: node.stop_track_effort(root)).grid(
            row=2, column=1, padx=5, pady=5, sticky=tk.W)

    def on_close():
        node.stop_blade_axis_effort(root, 'tilt')
        node.stop_blade_axis_effort(root, 'angle')
        node.stop_track_effort(root)
        node.destroy_node()
        rclpy.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    root.mainloop()

if __name__ == "__main__":
    main()
