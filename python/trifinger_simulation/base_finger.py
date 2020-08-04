import os
import warnings

import pybullet
from trifinger_simulation import pinocchio_utils
from trifinger_simulation import finger_types_data


class BaseFinger:
    """
    The SimFinger and RealFinger environments derive from this base
    class, which implements some common core functions.
    """

    def __init__(
        self, finger_type, enable_visualization,
    ):
        """
        Constructor sets up the requirements for either of the single or
        the trifinger robots.

        Args:
            finger_type (string): Name of the finger type.  Use
                get_valid_finger_types() to get a list of all supported types.
            enable_visualization (bool): Set this to 'True' for a GUI interface
                to the simulation.
        """
        self.enable_visualization = enable_visualization
        self.finger_type = finger_types_data.check_finger_type(finger_type)

        self.__set_finger_type_dependency()
        self.__init_joint_lists()
        self.__connect_to_simulation()
        self.pinocchio_utils = pinocchio_utils.PinocchioUtils(
            self.finger_urdf_path, self.tip_link_names
        )

    def __del__(self):
        """Clean up."""
        self._disconnect_from_simulation()

    def __connect_to_simulation(self):
        """
        Connect to the Pybullet client via either GUI (visual rendering
        enabled) or DIRECT (no visual rendering) physics servers.

        In GUI connection mode, use ctrl or alt with mouse scroll to adjust
        the view of the camera.
        """
        if not self.enable_simulation:
            return

        if self.enable_visualization:
            pybullet.connect(pybullet.GUI)
        else:
            pybullet.connect(pybullet.DIRECT)
            
    def _disconnect_from_simulation(self):
        """Disconnect from the simulation.

        Disconnects from the simulation and sets simulation to disabled to
        avoid any further function calls to it.
        """
        if self.enable_simulation:
            if pybullet.isConnected():
                pybullet.disconnect()
            self.enable_simulation = False

    def __set_finger_type_dependency(self):
        """
        Sets the paths for the URDFs to use depending upon the finger type
        """
        try:
            import rospkg

            self.robot_properties_path = rospkg.RosPack().get_path(
                "robot_properties_fingers"
            )
        except Exception:
            print(
                "Importing the robot description files from local copy "
                "of the robot_properties_fingers package."
            )
            self.robot_properties_path = os.path.join(
                os.path.dirname(__file__), "robot_properties_fingers"
            )

        if self.finger_type in ["single", "tri"]:
            warnings.warn(
                "Finger types 'single' and 'tri' are deprecated."
                " Use 'fingerone' and 'trifingerone' instead."
            )

        urdf_file = finger_types_data.get_finger_urdf(self.finger_type)
        self.finger_urdf_path = os.path.join(
            self.robot_properties_path, "urdf", urdf_file
        )
        self.number_of_fingers = finger_types_data.get_number_of_fingers(
            self.finger_type
        )

    def __init_joint_lists(self):
        """
        Initialize lists of link/joint names depending on which robot is used.
        """
        if self.number_of_fingers == 1:
            self.link_names = [
                "finger_upper_link",
                "finger_middle_link",
                "finger_lower_link",
            ]
            self.tip_link_names = ["finger_tip_link"]
        else:
            self.link_names = [
                "finger_upper_link_0",
                "finger_middle_link_0",
                "finger_lower_link_0",
                "finger_upper_link_120",
                "finger_middle_link_120",
                "finger_lower_link_120",
                "finger_upper_link_240",
                "finger_middle_link_240",
                "finger_lower_link_240",
            ]
            self.tip_link_names = [
                "finger_tip_link_0",
                "finger_tip_link_120",
                "finger_tip_link_240",
            ]

    def _load_robot_urdf(self):
        """
        Load the single/trifinger model from the corresponding urdf
        """
        if not self.enable_simulation:
            return

        finger_base_position = [0, 0, 0.0]
        finger_base_orientation = pybullet.getQuaternionFromEuler([0, 0, 0])

        self.finger_id = pybullet.loadURDF(
            fileName=self.finger_urdf_path,
            basePosition=finger_base_position,
            baseOrientation=finger_base_orientation,
            useFixedBase=1,
            flags=(
                pybullet.URDF_USE_INERTIA_FROM_FILE
                | pybullet.URDF_USE_SELF_COLLISION
            ),
        )

        # create a map link_name -> link_index
        # Source: https://pybullet.org/Bullet/phpBB3/viewtopic.php?t=12728.
        link_name_to_index = {
            pybullet.getBodyInfo(self.finger_id)[0].decode("UTF-8"): -1,
        }
        for joint_idx in range(pybullet.getNumJoints(self.finger_id)):
            link_name = pybullet.getJointInfo(self.finger_id, joint_idx)[
                12
            ].decode("UTF-8")
            link_name_to_index[link_name] = joint_idx
            
        self.pybullet_link_indices = [
            link_name_to_index[name] for name in self.link_names
        ]
        self.pybullet_tip_link_indices = [
            link_name_to_index[name] for name in self.tip_link_names
        ]
        # joint and link indices are the same in pybullet
        self.pybullet_joint_indices = self.pybullet_link_indices

