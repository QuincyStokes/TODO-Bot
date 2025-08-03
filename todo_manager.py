"""
Todo Manager Module

This module provides classes for managing todo lists and items.
Supports persistent storage, guild isolation, and user permissions.
"""

import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

# Create data directory for persistent storage
DATA_DIR = os.environ.get('DATA_DIR', '/opt/render/project/src/data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)


class TodoItem:
    """Represents a single todo item with completion tracking."""
    
    def __init__(self, content: str, created_by: str, item_id: str = None):
        """Initialize a todo item.
        
        Args:
            content: The text content of the todo item
            created_by: User ID of who created the item
            item_id: Optional custom ID for the item
        """
        self.content = content
        self.created_by = created_by
        self.completed = False
        self.completed_by = None
        self.completed_at = None
        self.created_at = datetime.now().isoformat()
        self.item_id = item_id or f"item_{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict:
        """Convert the item to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the item
        """
        return {
            'content': self.content,
            'created_by': self.created_by,
            'completed': self.completed,
            'completed_by': self.completed_by,
            'completed_at': self.completed_at,
            'created_at': self.created_at,
            'item_id': self.item_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TodoItem':
        """Create a TodoItem from a dictionary.
        
        Args:
            data: Dictionary containing item data
            
        Returns:
            TodoItem instance
        """
        try:
            item = cls(data.get('content', ''), data.get('created_by', ''), data.get('item_id'))
            item.completed = data.get('completed', False)
            item.completed_by = data.get('completed_by')
            item.completed_at = data.get('completed_at')
            item.created_at = data.get('created_at', datetime.now().isoformat())
            return item
        except Exception as e:
            print(f"Error creating TodoItem from dict: {e}")
            # Return a default item if data is corrupted
            return cls("Corrupted item", "unknown", data.get('item_id'))


class TodoList:
    """Represents a todo list containing multiple items."""
    
    def __init__(self, name: str, created_by: str, guild_id: str, list_id: str = None):
        """Initialize a todo list.
        
        Args:
            name: Name of the todo list
            created_by: User ID of who created the list
            guild_id: Discord server ID for guild isolation
            list_id: Optional custom ID for the list
        """
        self.name = name
        self.created_by = created_by
        self.guild_id = guild_id  # Discord server ID
        self.items: List[TodoItem] = []
        self.created_at = datetime.now().isoformat()
        self.list_id = list_id or f"list_{uuid.uuid4().hex[:8]}"
    
    def add_item(self, content: str, created_by: str) -> TodoItem:
        """Add a new item to this list.
        
        Args:
            content: The text content of the item
            created_by: User ID of who created the item
            
        Returns:
            The created TodoItem
        """
        item = TodoItem(content, created_by)
        self.items.append(item)
        return item
    
    def remove_item(self, item_id: str) -> bool:
        """Remove an item from this list.
        
        Args:
            item_id: ID of the item to remove
            
        Returns:
            True if item was removed, False if not found
        """
        for i, item in enumerate(self.items):
            if item.item_id == item_id:
                del self.items[i]
                return True
        return False
    
    def toggle_item(self, item_id: str, user_id: str) -> bool:
        """Toggle the completion status of an item.
        
        Args:
            item_id: ID of the item to toggle
            user_id: User ID of who is toggling the item
            
        Returns:
            True if item was toggled, False if not found
        """
        for item in self.items:
            if item.item_id == item_id:
                item.completed = not item.completed
                if item.completed:
                    item.completed_by = user_id
                    item.completed_at = datetime.now().isoformat()
                else:
                    item.completed_by = None
                    item.completed_at = None
                return True
        return False
    
    def get_item(self, item_id: str) -> Optional[TodoItem]:
        """Get an item by ID.
        
        Args:
            item_id: ID of the item to find
            
        Returns:
            TodoItem if found, None otherwise
        """
        for item in self.items:
            if item.item_id == item_id:
                return item
        return None
    
    def to_dict(self) -> Dict:
        """Convert the list to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the list
        """
        return {
            'name': self.name,
            'created_by': self.created_by,
            'guild_id': self.guild_id,
            'items': [item.to_dict() for item in self.items],
            'created_at': self.created_at,
            'list_id': self.list_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TodoList':
        """Create a TodoList from a dictionary.
        
        Args:
            data: Dictionary containing list data
            
        Returns:
            TodoList instance
        """
        try:
            todo_list = cls(
                data.get('name', 'Unknown List'),
                data.get('created_by', 'unknown'),
                data.get('guild_id', 'unknown'),
                data.get('list_id')
            )
            todo_list.created_at = data.get('created_at', datetime.now().isoformat())
            
            # Load items with error handling
            items_data = data.get('items', [])
            for item_data in items_data:
                try:
                    item = TodoItem.from_dict(item_data)
                    todo_list.items.append(item)
                except Exception as e:
                    print(f"Error loading item: {e}")
                    continue
            
            return todo_list
        except Exception as e:
            print(f"Error creating TodoList from dict: {e}")
            # Return a default list if data is corrupted
            return cls("Corrupted List", "unknown", "unknown", data.get('list_id'))


class TodoManager:
    """Manages todo lists with persistent storage and guild isolation."""
    
    def __init__(self, storage_file: str = 'todo_lists.json'):
        """Initialize the todo manager.
        
        Args:
            storage_file: Name of the JSON file for persistent storage
        """
        # Handle both relative and absolute paths
        if os.path.isabs(storage_file):
            self.storage_file = storage_file
        else:
            self.storage_file = os.path.join(DATA_DIR, storage_file)
        self.todo_lists: Dict[str, TodoList] = {}
        self._last_save_time = 0
        self._save_interval = 0.1  # Save at most once per 0.1 seconds (more frequent)
        self.load_lists()
    
    def __del__(self):
        """Destructor to ensure data is saved."""
        self.force_save()
    
    def load_lists(self):
        """Load todo lists from JSON file with error handling."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.todo_lists = {}
                    for list_id, list_data in data.items():
                        try:
                            todo_list = TodoList.from_dict(list_data)
                            self.todo_lists[list_id] = todo_list
                        except Exception as e:
                            print(f"Error loading todo list {list_id}: {e}")
                            continue
            except (json.JSONDecodeError, KeyError, IOError) as e:
                print(f"Error loading todo lists: {e}")
                self.todo_lists = {}
    
    def save_lists(self):
        """Save todo lists to JSON file with rate limiting and error handling."""
        current_time = time.time()
        
        # Only save if enough time has passed since last save
        if current_time - self._last_save_time < self._save_interval:
            return
        
        try:
            data = {}
            for list_id, todo_list in self.todo_lists.items():
                try:
                    data[list_id] = todo_list.to_dict()
                except Exception as e:
                    print(f"Error serializing todo list {list_id}: {e}")
                    continue
            
            # Create backup before writing
            if os.path.exists(self.storage_file):
                backup_file = f"{self.storage_file}.backup"
                try:
                    import shutil
                    shutil.copy2(self.storage_file, backup_file)
                except Exception as e:
                    print(f"Error creating backup: {e}")
            
            # Write to temporary file first, then rename
            temp_file = f"{self.storage_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            os.replace(temp_file, self.storage_file)
            self._last_save_time = current_time
            
        except Exception as e:
            print(f"Error saving todo lists: {e}")
    
    def force_save(self):
        """Force save regardless of rate limiting."""
        try:
            data = {}
            for list_id, todo_list in self.todo_lists.items():
                try:
                    data[list_id] = todo_list.to_dict()
                except Exception as e:
                    print(f"Error serializing todo list {list_id}: {e}")
                    continue
            
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._last_save_time = time.time()
        except Exception as e:
            print(f"Error saving todo lists: {e}")
    
    def create_list(self, name: str, created_by: str, guild_id: str) -> TodoList:
        """Create a new todo list.
        
        Args:
            name: Name of the todo list
            created_by: User ID of who created the list
            guild_id: Discord server ID for guild isolation
            
        Returns:
            The created TodoList
        """
        if self.list_exists(name, guild_id):
            # If list with the same name already exists, append a number to the name
            existing_lists = self.get_lists_by_name(name, guild_id)
            new_name = f"{name} (1)"
            i = 2
            while self.list_exists(new_name, guild_id):
                new_name = f"{name} ({i})"
                i += 1
            name = new_name
            print(f"List with name '{name}' already exists. Renaming to '{new_name}'.")

        todo_list = TodoList(name, created_by, guild_id)
        self.todo_lists[todo_list.list_id] = todo_list
        self.save_lists()
        return todo_list
    
    def get_list(self, list_id: str) -> Optional[TodoList]:
        """Get a todo list by ID.
        
        Args:
            list_id: ID of the list to find
            
        Returns:
            TodoList if found, None otherwise
        """
        return self.todo_lists.get(list_id)
    
    def get_list_by_name(self, name: str, guild_id: str) -> Optional[TodoList]:
        """Get a todo list by name within a specific guild.
        
        Args:
            name: Name of the list to find
            guild_id: Discord server ID for guild isolation
            
        Returns:
            TodoList if found, None otherwise
        """
        for todo_list in self.todo_lists.values():
            if todo_list.name == name and todo_list.guild_id == guild_id:
                return todo_list
        return None
    
    def get_lists_by_name(self, name: str, guild_id: str) -> List[TodoList]:
        """Get all todo lists with the same name within a specific guild.
        
        Args:
            name: Name of the list to find
            guild_id: Discord server ID for guild isolation
            
        Returns:
            List of TodoList objects with the given name in the guild
        """
        return [
            todo_list for todo_list in self.todo_lists.values()
            if todo_list.name == name and todo_list.guild_id == guild_id
        ]
    
    def list_exists(self, name: str, guild_id: str) -> bool:
        """Check if a list with the given name exists in the guild.
        
        Args:
            name: Name of the list to check
            guild_id: Discord server ID for guild isolation
            
        Returns:
            True if a list with that name exists, False otherwise
        """
        return self.get_list_by_name(name, guild_id) is not None
    
    def delete_list(self, list_id: str) -> bool:
        """Delete a todo list.
        
        Args:
            list_id: ID of the list to delete
            
        Returns:
            True if list was deleted, False if not found
        """
        if list_id in self.todo_lists:
            del self.todo_lists[list_id]
            self.save_lists()
            return True
        return False
    
    def get_all_lists(self, guild_id: str) -> List[TodoList]:
        """Get all todo lists for a specific guild.
        
        Args:
            guild_id: Discord server ID for guild isolation
            
        Returns:
            List of TodoList objects for the guild
        """
        return [
            todo_list for todo_list in self.todo_lists.values()
            if todo_list.guild_id == guild_id
        ]
    
    def add_item_to_list(self, list_id: str, content: str, created_by: str) -> Optional[TodoItem]:
        """Add an item to a specific todo list.
        
        Args:
            list_id: ID of the list to add to
            content: The text content of the item
            created_by: User ID of who created the item
            
        Returns:
            The created TodoItem if successful, None otherwise
        """
        todo_list = self.get_list(list_id)
        if todo_list:
            item = todo_list.add_item(content, created_by)
            self.save_lists()
            return item
        return None
    
    def remove_item_from_list(self, list_id: str, item_id: str) -> bool:
        """Remove an item from a specific todo list.
        
        Args:
            list_id: ID of the list to remove from
            item_id: ID of the item to remove
            
        Returns:
            True if item was removed, False if not found
        """
        todo_list = self.get_list(list_id)
        if todo_list:
            success = todo_list.remove_item(item_id)
            if success:
                self.save_lists()
            return success
        return False
    
    def toggle_item_in_list(self, list_id: str, item_id: str, user_id: str) -> bool:
        """Toggle the completion status of an item in a specific todo list.
        
        Args:
            list_id: ID of the list containing the item
            item_id: ID of the item to toggle
            user_id: User ID of who is toggling the item
            
        Returns:
            True if item was toggled, False if not found
        """
        todo_list = self.get_list(list_id)
        if todo_list:
            success = todo_list.toggle_item(item_id, user_id)
            if success:
                self.save_lists()
            return success
        return False 