#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.duration import Duration
import asyncio

class NavigationClient(Node):
    def __init__(self):
        super().__init__('navigation_client')
        self.action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.get_logger().info('Navigation client initialized')
        
        # Define coordinates for different locations
        self.locations = {
            'initial_pose': {'x': -0.04, 'y': -0.06, 'z': 0.0},
            'medical_shop': {'x': 26.36, 'y': -6.18, 'z': 0.0},
            'room1': {'x': 10.97, 'y': 4.0, 'z': 0.0},
            'room2': {'x': 15.92, 'y': -4.0, 'z': 0.0}
        }

    async def navigate_to_position(self, x, y, z, orientation_w=1.0):
        while not self.action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().info('Waiting for action server...')

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.position.z = z
        
        goal_msg.pose.pose.orientation.w = orientation_w
        goal_msg.pose.pose.orientation.x = 0.0
        goal_msg.pose.pose.orientation.y = 0.0
        goal_msg.pose.pose.orientation.z = 0.0

        self.get_logger().info(f'Navigating to position: x={x}, y={y}, z={z}')
        
        send_goal_future = self.action_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        
        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected')
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        
        self.get_logger().info('Navigation completed')
        return True

    async def deliver_medicine(self, order_number):
        # First navigate to medical shop
        self.get_logger().info('Moving to medical shop to collect medicine...')
        await self.navigate_to_position(**self.locations['medical_shop'])
        
        # Wait at medical shop
        self.get_logger().info('Collecting medicine...')
        await asyncio.sleep(15.0)
        
        # Navigate to the specified room
        room = 'room1' if order_number == 1 else 'room2'
        self.get_logger().info(f'Delivering medicine to {room}...')
        await self.navigate_to_position(**self.locations[room])
        
        # Wait at room for delivery
        self.get_logger().info('Delivering medicine...')
        await asyncio.sleep(10.0)
        
        # Return to initial position
        self.get_logger().info('Returning to initial position...')
        await self.navigate_to_position(**self.locations['initial_pose'])
        
        self.get_logger().info('Delivery completed!')

async def main():
    try:
        rclpy.init()
        navigator = NavigationClient()
        
        while True:
            try:
                # Get order input from user
                order = input("Enter order number (1 for Room1, 2 for Room2, q to quit): ")
                
                if order.lower() == 'q':
                    break
                    
                if order not in ['1', '2']:
                    print("Invalid order number. Please enter 1 or 2.")
                    continue
                
                # Execute delivery
                await navigator.deliver_medicine(int(order))
                
            except KeyboardInterrupt:
                navigator.get_logger().info('Navigation cancelled by user')
                break
            except Exception as e:
                navigator.get_logger().error(f'Error during navigation: {str(e)}')
                continue
                
    except Exception as e:
        print(f"Error initializing ROS 2: {str(e)}")
    finally:
        navigator.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    asyncio.run(main())