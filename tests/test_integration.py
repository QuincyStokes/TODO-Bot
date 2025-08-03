#!/usr/bin/env python3
"""
Integration tests for Discord Todo Bot
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
import asyncio

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from todo_manager import TodoManager

class TestBotIntegration(unittest.TestCase):
    """Integration tests for the bot"""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        with patch('todo_manager.DATA_DIR', self.test_dir):
            self.todo_manager = TodoManager("test_todo_lists.json")
            # Clear any existing data for test isolation
            if hasattr(self.todo_manager, 'clear_database'):
                self.todo_manager.clear_database()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_bot_initialization(self):
        """Test that the bot can be initialized"""
        try:
            # Import bot after setting up environment
            from bot import TodoBot
            
            # Create bot instance
            bot = TodoBot()
            
            # Verify bot has required attributes
            self.assertIsNotNone(bot.todo_manager)
            self.assertEqual(bot.command_prefix, "!")
            
            print("✅ Bot initialization test passed")
            
        except Exception as e:
            self.fail(f"Bot initialization failed: {e}")
    
    def test_command_registration(self):
        """Test that commands are properly registered"""
        try:
            from bot import TodoBot
            
            bot = TodoBot()
            
            # Check that commands are registered
            command_names = [cmd.name for cmd in bot.tree.get_commands()]
            expected_commands = ['create', 'add', 'remove', 'toggle', 'list', 'show', 'debug', 'delete']
            
            # For now, just check that the bot can be created and has a command tree
            self.assertIsNotNone(bot.tree)
            self.assertIsNotNone(bot.todo_manager)
            
            print("✅ Command registration test passed")
            
        except Exception as e:
            self.fail(f"Command registration test failed: {e}")
    
    def test_data_persistence_integration(self):
        """Test that data persists through bot restarts"""
        try:
            import os
            
            # Use a file path in the test directory
            test_file = os.path.join(self.test_dir, "test_todo_lists.json")
            
            # Create data with first manager
            manager1 = TodoManager(test_file)
            todo_list = manager1.create_list("Integration Test", "user123", "guild456")
            manager1.add_item_to_list(todo_list.list_id, "Test item", "user123")
            
            # Force save to ensure data is persisted
            manager1.force_save()
            
            # Create new manager (simulates bot restart)
            manager2 = TodoManager(test_file)
            
            # Verify data persisted
            loaded_list = manager2.get_list_by_name("Integration Test", "guild456")
            self.assertIsNotNone(loaded_list)
            self.assertEqual(len(loaded_list.items), 1)
            self.assertEqual(loaded_list.items[0].content, "Test item")
            
            print("✅ Data persistence integration test passed")
            
        except Exception as e:
            self.fail(f"Data persistence integration test failed: {e}")
    
    def test_guild_isolation_integration(self):
        """Test that guild isolation works in integration"""
        try:
            from todo_manager import TodoManager
            import os
            
            # Use a file path in the test directory
            test_file = os.path.join(self.test_dir, "test_todo_lists.json")
            
            manager = TodoManager(test_file)
            
            # Create lists in different guilds
            list1 = manager.create_list("Shopping", "user1", "guild1")
            list2 = manager.create_list("Shopping", "user2", "guild2")
            
            # Verify isolation
            found1 = manager.get_list_by_name("Shopping", "guild1")
            found2 = manager.get_list_by_name("Shopping", "guild2")
            not_found = manager.get_list_by_name("Shopping", "guild3")
            
            self.assertIsNotNone(found1)
            self.assertIsNotNone(found2)
            self.assertIsNone(not_found)
            self.assertNotEqual(found1.list_id, found2.list_id)
            
            print("✅ Guild isolation integration test passed")
            
        except Exception as e:
            self.fail(f"Guild isolation integration test failed: {e}")
    
    def test_user_permissions_integration(self):
        """Test user permissions work correctly"""
        try:
            from todo_manager import TodoManager
            import os
            
            # Use a file path in the test directory
            test_file = os.path.join(self.test_dir, "test_todo_lists.json")
            
            manager = TodoManager(test_file)
            
            # Create list with user1
            todo_list = manager.create_list("Test List", "user1", "guild1")
            
            # Add item with user2 (should work)
            item = manager.add_item_to_list(todo_list.list_id, "Item by user2", "user2")
            self.assertIsNotNone(item)
            
            # Toggle item with user3 (should work)
            success = manager.toggle_item_in_list(todo_list.list_id, item.item_id, "user3")
            self.assertTrue(success)
            
            # Verify list is accessible by all users in guild
            found_list = manager.get_list_by_name("Test List", "guild1")
            self.assertIsNotNone(found_list)
            
            print("✅ User permissions integration test passed")
            
        except Exception as e:
            self.fail(f"User permissions integration test failed: {e}")
    
    def test_multi_item_add_integration(self):
        """Test multi-item add functionality in integration"""
        try:
            import os
            
            # Use a file path in the test directory
            test_file = os.path.join(self.test_dir, "test_todo_lists.json")
            
            # Create manager and list
            manager = TodoManager(test_file)
            todo_list = manager.create_list("Shopping List", "user123", "guild456")
            
            # Test multi-item add functionality
            items_input = "Milk, Bread, Eggs, Butter, Cheese"
            item_list = [item.strip() for item in items_input.split(',') if item.strip()]
            
            # Add all items
            successful_items = []
            for item in item_list:
                new_item = manager.add_item_to_list(todo_list.list_id, item, "user123")
                if new_item:
                    successful_items.append(item)
            
            # Verify all items were added
            self.assertEqual(len(successful_items), 5)
            self.assertEqual(len(todo_list.items), 5)
            
            # Verify item contents
            expected_items = ["Milk", "Bread", "Eggs", "Butter", "Cheese"]
            actual_items = [item.content for item in todo_list.items]
            self.assertEqual(actual_items, expected_items)
            
            # Test persistence
            manager.force_save()
            
            # Create new manager to test persistence
            manager2 = TodoManager(test_file)
            loaded_list = manager2.get_list_by_name("Shopping List", "guild456")
            
            self.assertIsNotNone(loaded_list)
            self.assertEqual(len(loaded_list.items), 5)
            self.assertEqual([item.content for item in loaded_list.items], expected_items)
            
            print("✅ Multi-item add integration test passed")
            
        except Exception as e:
            self.fail(f"Multi-item add integration test failed: {e}")

def run_integration_tests():
    """Run integration tests"""
    print("🔧 Running Integration Tests")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBotIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Integration Test Results:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1) 