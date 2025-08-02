import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class TodoItem:
    def __init__(self, content: str, created_by: str, item_id: str = None):
        self.content = content
        self.created_by = created_by
        self.completed = False
        self.completed_by = None
        self.completed_at = None
        self.created_at = datetime.now().isoformat()
        self.item_id = item_id or f"item_{datetime.now().timestamp()}"
    
    def to_dict(self):
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
    def from_dict(cls, data: dict):
        item = cls(data['content'], data['created_by'], data['item_id'])
        item.completed = data['completed']
        item.completed_by = data['completed_by']
        item.completed_at = data['completed_at']
        item.created_at = data['created_at']
        return item

class TodoList:
    def __init__(self, name: str, created_by: str, list_id: str = None):
        self.name = name
        self.created_by = created_by
        self.items: List[TodoItem] = []
        self.created_at = datetime.now().isoformat()
        self.list_id = list_id or f"list_{datetime.now().timestamp()}"
    
    def add_item(self, content: str, created_by: str) -> TodoItem:
        item = TodoItem(content, created_by)
        self.items.append(item)
        return item
    
    def remove_item(self, item_id: str) -> bool:
        for i, item in enumerate(self.items):
            if item.item_id == item_id:
                del self.items[i]
                return True
        return False
    
    def toggle_item(self, item_id: str, user_id: str) -> bool:
        for item in self.items:
            if item.item_id == item_id:
                if item.completed:
                    item.completed = False
                    item.completed_by = None
                    item.completed_at = None
                else:
                    item.completed = True
                    item.completed_by = user_id
                    item.completed_at = datetime.now().isoformat()
                return True
        return False
    
    def get_item(self, item_id: str) -> Optional[TodoItem]:
        for item in self.items:
            if item.item_id == item_id:
                return item
        return None
    
    def to_dict(self):
        return {
            'name': self.name,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'list_id': self.list_id,
            'items': [item.to_dict() for item in self.items]
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        todo_list = cls(data['name'], data['created_by'], data['list_id'])
        todo_list.created_at = data['created_at']
        todo_list.items = [TodoItem.from_dict(item_data) for item_data in data['items']]
        return todo_list

class TodoManager:
    def __init__(self, storage_file: str = 'todo_lists.json'):
        self.storage_file = storage_file
        self.todo_lists: Dict[str, TodoList] = {}
        self.load_lists()
    
    def load_lists(self):
        """Load todo lists from JSON file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.todo_lists = {
                        list_id: TodoList.from_dict(list_data)
                        for list_id, list_data in data.items()
                    }
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading todo lists: {e}")
                self.todo_lists = {}
    
    def save_lists(self):
        """Save todo lists to JSON file"""
        try:
            data = {
                list_id: todo_list.to_dict()
                for list_id, todo_list in self.todo_lists.items()
            }
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving todo lists: {e}")
    
    def create_list(self, name: str, created_by: str) -> TodoList:
        """Create a new todo list"""
        todo_list = TodoList(name, created_by)
        self.todo_lists[todo_list.list_id] = todo_list
        self.save_lists()
        return todo_list
    
    def get_list(self, list_id: str) -> Optional[TodoList]:
        """Get a todo list by ID"""
        return self.todo_lists.get(list_id)
    
    def get_list_by_name(self, name: str) -> Optional[TodoList]:
        """Get a todo list by name"""
        for todo_list in self.todo_lists.values():
            if todo_list.name.lower() == name.lower():
                return todo_list
        return None
    
    def delete_list(self, list_id: str) -> bool:
        """Delete a todo list"""
        if list_id in self.todo_lists:
            del self.todo_lists[list_id]
            self.save_lists()
            return True
        return False
    
    def get_all_lists(self) -> List[TodoList]:
        """Get all todo lists"""
        return list(self.todo_lists.values())
    
    def add_item_to_list(self, list_id: str, content: str, created_by: str) -> Optional[TodoItem]:
        """Add an item to a specific todo list"""
        todo_list = self.get_list(list_id)
        if todo_list:
            item = todo_list.add_item(content, created_by)
            self.save_lists()
            return item
        return None
    
    def remove_item_from_list(self, list_id: str, item_id: str) -> bool:
        """Remove an item from a specific todo list"""
        todo_list = self.get_list(list_id)
        if todo_list:
            success = todo_list.remove_item(item_id)
            if success:
                self.save_lists()
            return success
        return False
    
    def toggle_item_in_list(self, list_id: str, item_id: str, user_id: str) -> bool:
        """Toggle completion status of an item"""
        todo_list = self.get_list(list_id)
        if todo_list:
            success = todo_list.toggle_item(item_id, user_id)
            if success:
                self.save_lists()
            return success
        return False 