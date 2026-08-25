#!/usr/bin/env python3
"""
Ollama Client implementation with persona and manifest support.
"""

import os
import json
from typing import Dict, List, Optional, Any

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", personas_dir: str = "./personas", manifests_dir: str = "./manifests"):
        self.base_url = base_url
        self.personas_dir = personas_dir
        self.manifests_dir = manifests_dir
        self.loaded_personas = {}
        self.loaded_manifests = {}
        
        # Ensure directories exist
        os.makedirs(self.personas_dir, exist_ok=True)
        os.makedirs(self.manifests_dir, exist_ok=True)

    def get_available_models(self) -> List[str]:
        # In a real implementation, we would query the Ollama API.
        # For now, we return a stub.
        return ["qwen2.5-coder:7b"]

    def load_persona(self, persona_name: str) -> str:
        """Load a persona from the personas directory."""
        if persona_name in self.loaded_personas:
            return self.loaded_personas[persona_name]
        
        persona_path = os.path.join(self.personas_dir, f"{persona_name}.md")
        if os.path.exists(persona_path):
            with open(persona_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.loaded_personas[persona_name] = content
                return content
        else:
            # Fallback to basic persona if file not found
            default_persona = f"Persona: {persona_name}"
            self.loaded_personas[persona_name] = default_persona
            return default_persona

    def load_manifest(self, manifest_name: str) -> str:
        """Load a tool manifest from the manifests directory."""
        if manifest_name in self.loaded_manifests:
            return self.loaded_manifests[manifest_name]
        
        manifest_path = os.path.join(self.manifests_dir, f"{manifest_name}.md")
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.loaded_manifests[manifest_name] = content
                return content
        else:
            # Fallback to basic manifest if file not found
            default_manifest = f"Manifest: {manifest_name}"
            self.loaded_manifests[manifest_name] = default_manifest
            return default_manifest

    def chat(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.0, format_json: bool = False, 
             persona: str = None, manifest: str = None) -> Dict[str, Any]:
        """
        Send a chat message to the Ollama LLM with optional persona and manifest.
        
        Args:
            model: The model to use
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature
            format_json: Whether to request JSON format output
            persona: Name of persona to load and use
            manifest: Name of manifest to load and use
        """
        # Load persona and manifest if specified
        persona_content = ""
        manifest_content = ""
        
        if persona:
            persona_content = self.load_persona(persona)
        
        if manifest:
            manifest_content = self.load_manifest(manifest)
        
        # Construct the system message with persona and manifest
        system_parts = []
        if persona_content:
            system_parts.append(persona_content)
        if manifest_content:
            system_parts.append(manifest_content)
        
        system_message = "\n\n".join(system_parts) if system_parts else ""
        
        # Prepare messages for the LLM
        llm_messages = []
        if system_message:
            llm_messages.append({"role": "system", "content": system_message})
        llm_messages.extend(messages)
        
        # In a real implementation, we would make an HTTP request to the Ollama API here.
        # For now, we return a stub response that incorporates the persona and manifest.
        
        # Determine suggested action based on persona content (simplified)
        suggested_action = "HOLD"
        confidence = 0.5
        if persona:
            if "researcher" in persona.lower():
                # For researcher persona, sometimes generate a signal
                import random
                if random.random() > 0.3:  # 70% chance of generating a signal
                    suggested_action = "BUY" if random.random() > 0.5 else "SELL"
                    confidence = 0.6 + random.random() * 0.3  # 0.6-0.9 confidence
        
        return {
            "status": "success",
            "json_data": {
                "action": suggested_action,
                "confidence": confidence,
                "target_price": 200.0,
                "stop_loss": 190.0,
                "take_profit": 210.0,
                "suggested_quantity": 100,
                "thesis": f"Analysis performed with {persona or 'default'} persona and {manifest or 'default'} manifest."
            },
            "thinking": f"Used persona: {persona or 'none'}, manifest: {manifest or 'none'}"
        }