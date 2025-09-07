import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv
from typing import Dict, Any
import base64
import cairosvg
import requests
from mimetypes import guess_type

# Load environment variables
load_dotenv()

class BannerAgent:

    def __init__(self, model_name="gpt-5-nano"):
        llm_kwargs = {
            "model": model_name,
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "max_retries": 3,
            "temperature": 1.0,
            "model_kwargs": {
                # Sửa cảnh báo UserWarning: chuyển max_completion_tokens vào đây
                # và đổi tên thành max_tokens theo chuẩn của OpenAI API
                "max_completion_tokens": 8192 
            }
        }

        self.llm = ChatOpenAI(**llm_kwargs)
        self.json_llm = self.llm.bind(
            response_format={"type": "json_object"}
        )

        self.load_prompts()
    
    def load_prompts(self):
        """Load all system prompts"""
        try:
            from prompts.strategist_prompt import strategist_system_prompt, strategist_context_prompt
            from prompts.background_designer_prompt import background_designer_system_prompt, background_designer_context_prompt
            from prompts.foreground_designer_prompt import foreground_designer_system_prompt, foreground_designer_context_prompt
            from prompts.design_reviewer_prompt import system_prompt as reviewer_system_prompt
            from prompts.developer_prompt import developer_prompt
            from prompts.visual_asset_prompt import visual_asset_system_prompt, visual_asset_context_prompt
            
            self.prompts = {
            'strategist_context_prompt': strategist_context_prompt,    
            'strategist_system_prompt': strategist_system_prompt,
            
            'visual_asset_system_prompt': visual_asset_system_prompt,
            'visual_asset_context_prompt': visual_asset_context_prompt,
            
            'background_designer_system_prompt': background_designer_system_prompt,
            'background_designer_context_prompt': background_designer_context_prompt,
            
            'foreground_designer_system_prompt': foreground_designer_system_prompt,
            'foreground_designer_context_prompt': foreground_designer_context_prompt,
            
            'design_reviewer': reviewer_system_prompt,
            'developer': developer_prompt
        }
            print("✅ Loaded prompts from files")
        except ImportError as e:
            print(f"Warning: Could not load prompts: {e}")
            # Fallback to basic prompts
            self.setup_fallback_prompts()
    
    def setup_fallback_prompts(self):
        """Setup basic fallback prompts if imports fail"""
        self.prompts = {
            'strategist': """You are an expert banner objective setter. When a user requests a banner, consider their requirements and develop high-level objectives for an effective banner that would:
- Support the banner's primary purpose
- Create appropriate mood and tone  
- Appeal to the target audience

Analyze the request and provide:
1. Primary Purpose (brand awareness, lead generation, sales, event promotion)
2. Target Audience (demographics, interests, behavior)
3. Mood and Tone (professional, playful, urgent, luxurious, etc.)""",

            'background_designer': """You are an image director specialized in banner backgrounds. Your goal is to create a nice background canvas for foreground elements to be placed. 

When creating the supporting background image, you should:
1. Analyze and consider the provided objectives, user requirements, and provided logo
2. Create a detailed background description considering visual style, mood, color schemes, composition elements, and focal points
3. Focus only on the background's visual and structural elements
4. Avoid mentioning ANY brand/logo names or text elements
5. Ensure the background is free of text elements""",

            'foreground_designer': """You are a textual director specialized in banner layout and typography. Your role is to create precise, varied layouts that follow established design patterns while maintaining visual hierarchy and readability.

Create complete layout specifications with:
1. Typography Hierarchy (headline, subheadline, body text)
2. CTA button design and positioning  
3. Logo placement and sizing
4. Color and contrast considerations
5. Responsive spacing based on banner size
6. Creative and matching font selection""",

            'design_reviewer': """You are an experienced marketing professional in the advertisement industry reviewing a banner ad under development. 
You are iteratively evaluating the foreground elements (text, buttons, etc.) based on their fit with the background.
If the foreground elements are not perfect for production, provide key FEEDBACK on ways to improve. If it looks good overall, approve it.

Focus on:
- Element positioning and overlaps
- Logo placement and visibility  
- Font types, colors, and button design
- Overall professional marketing quality""",

            'developer': """You are a Figma plugin developer. Your tasks:
1. Update ui.html with background and logo image names
2. Follow the JavaScript template
3. Generate and save plugin code with layout implementation
4. Render the image and provide the file path
5. Backup plugin files"""
        }
        print("✅ Using fallback prompts")
    
    def prepare_image_message(self, image_path: str) -> str:
        """Convert image to base64 for API"""
        try:
            mime_type, _ = guess_type(image_path)
            if mime_type is None:
                mime_type = "application/octet-stream"
            
            with open(image_path, "rb") as image_file:
                base64_encoded_data = base64.b64encode(image_file.read()).decode("utf-8")
            
            return f"data:{mime_type};base64,{base64_encoded_data}"
        except Exception as e:
            raise ValueError(f"Failed to process image at {image_path}: {str(e)}")
    
    def strategist_agent(self, user_input: str, logo_path: str = None) -> Dict[str, Any]:
        """
        Strategist Agent: Analyzes requirements and logo image, then returns a structured
        JSON object containing the creative direction (theme, mood, color_palette).
        """
        print("🎯 Strategist Agent: Analyzing requirements...")
        
        # Sử dụng prompt hệ thống mới, yêu cầu output JSON
        system_prompt = self.prompts['strategist_system_prompt']
        
        # Xây dựng context prompt mới, bao gồm cả user_input và logo_path
        context_text = self.prompts['strategist_context_prompt'].format(
            user_input=user_input,
            logo_path=logo_path if logo_path else "No logo provided."
        )
        
        content = [{"type": "text", "text": context_text}]
        
        # Thêm ảnh logo vào message nếu có
        if logo_path and os.path.exists(logo_path):
            logo_data = self.prepare_image_message(logo_path)
            content.extend([
                {"type": "text", "text": "\nAnalyze the color scheme from this logo:"},
                {"type": "image_url", "image_url": {"url": logo_data}}
            ])
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=content)
        ]
        
        try:
            # Quan trọng: Dùng self.json_llm để bắt buộc output là JSON
            response = self.json_llm.invoke(messages)
            
            # Chuyển đổi chuỗi JSON trả về thành từ điển Python
            objectives = json.loads(response.content)
            
            print(f"✅ Strategist objectives set: {objectives}")
            return objectives
            
        except Exception as e:
            print(f"⚠️ Strategist error: {e}")
            # Fallback an toàn, trả về một dict rỗng để không làm sập hệ thống
            return {
                "theme": "General",
                "mood": "Professional",
                "color_palette": {
                    "background": "#F0F0F0",
                    "text": "#000000",
                    "accent": "#007BFF"
                }
            }
    
    def parse_objectives(self, response: str) -> Dict[str, str]:
        """Parse objectives from strategist response"""
        objectives = {
            'purpose': 'Brand Awareness',
            'audience': 'General Public',
            'mood': 'Professional'
        }
        
        # Simple parsing
        lines = response.split('\n')
        for line in lines:
            line_lower = line.lower()
            if 'purpose' in line_lower and ':' in line:
                objectives['purpose'] = line.split(':', 1)[-1].strip()
            elif 'audience' in line_lower and ':' in line:
                objectives['audience'] = line.split(':', 1)[-1].strip()
            elif 'mood' in line_lower or 'tone' in line_lower and ':' in line:
                objectives['mood'] = line.split(':', 1)[-1].strip()
        
        return objectives
    

    def background_designer_agent(self, theme: str, mood: str, color_palette: Dict[str, str], hero_image_path: str = None) -> Dict[str, Any]:
        """
        Art Director Agent: Decides the overall composition by combining
        a hero image and a structured background.
        """
        print("🎬 Art Director (Background Designer): Designing composition...")
        system_prompt = self.prompts['background_designer_system_prompt']
        
        # Thêm hero_image_path vào context
        context_prompt = self.prompts['background_designer_context_prompt'].format(
            theme=theme,
            mood=mood,
            color_palette=str(color_palette),
            hero_image_path=hero_image_path
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_prompt)
        ]
        
        try:
            response = self.json_llm.invoke(messages)
            structure = json.loads(response.content)
            print(f"✅ Composition designed: {structure}")
            return structure
        except Exception as e:
            print(f"⚠️ Art Director error: {e}")
            # Fallback an toàn, ưu tiên có ảnh nếu có
            if hero_image_path:
                return {
                    "composition_type": "full_bleed", "hero_image_path": hero_image_path,
                    "background_structure": {"base_layer": {"type": "solid", "colors": ["#000000"]}, "overlay_layer": {"type": "none"}},
                    "text_overlay": {"apply": True, "color": "#000000", "opacity": 0.5}
                }
            else: # Fallback không có ảnh
                return {
                    "composition_type": "background_only", "hero_image_path": None,
                    "background_structure": {"base_layer": {"type": "solid", "colors": ["#CCCCCC"]}, "overlay_layer": {"type": "none"}},
                    "text_overlay": {"apply": False}
                }
    
 
    def foreground_designer_agent(self, user_input: str, objectives: Dict[str, Any], 
                                width: int, height: int) -> Dict[str, Any]:
        """
        Foreground Designer Agent: Creates layout and typography specifications.
        It translates the new rich color palette into the simple format expected by the prompt.
        """
        print("📝 Foreground Designer Agent: Designing layout...")
        
        rich_color_palette = objectives.get('color_palette', {})
        theme = objectives.get('theme', 'general')
        mood = objectives.get('mood', 'professional')

        # --- BƯỚC PHIÊN DỊCH QUAN TRỌNG ---
        # Dịch từ bảng màu mới (rich) sang bảng màu cũ (simple) mà prompt đang mong đợi.
        simple_color_palette = {
            "text": rich_color_palette.get("primary_text", "#000000"), # Lấy primary_text, fallback về màu đen
            "accent": rich_color_palette.get("accent_1", "#007BFF")    # Lấy accent_1, fallback về màu xanh
        }
        # --- KẾT THÚC BƯỚC PHIÊN DỊCH ---

        system_prompt = self.prompts.get('foreground_designer_system_prompt')
        
        # Giờ đây, chúng ta truyền `simple_color_palette` vào prompt.
        # Prompt sẽ nhận được chính xác những gì nó mong đợi.
        context_prompt = self.prompts.get('foreground_designer_context_prompt').format(
            width=width,
            height=height,
            user_input=user_input,
            theme=theme,
            mood=mood,
            color_palette=str(simple_color_palette) # TRUYỀN BẢNG MÀU ĐÃ ĐƯỢC DỊCH
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_prompt)
        ]
        
        try:
            response = self.json_llm.invoke(messages)
            # Sửa đổi quan trọng: dùng json.loads trực tiếp để ổn định hơn
            layout_spec = json.loads(response.content)
            print("✅ Foreground layout designed")
            return layout_spec
        except Exception as e:
            print(f"⚠️ Foreground designer error: {e}")
            # Thử parse lại một lần nữa nếu json.loads thất bại
            return self.parse_layout_specification(response.content, width, height)
    
    def parse_layout_specification(self, response: str, width: int, height: int) -> Dict[str, Any]:
        """Parse structured layout specification from LLM response"""
        try:
            # Tìm đoạn JSON trong response
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                layout_json = response[start:end+1]
                layout = json.loads(layout_json)
                return layout
        except Exception as e:
            print(f"⚠️ Parse layout JSON error: {e}")
        
        # Nếu thất bại → fallback
        return self.get_fallback_layout(width, height)
    
    def get_fallback_layout(self, width: int, height: int) -> Dict[str, Any]:
        """Generate fallback layout based on dimensions"""
        # Scale elements based on banner size
        headline_size = max(24, min(width // 20, height // 8))
        subheadline_size = max(16, min(width // 30, height // 12))
        cta_width = max(100, min(width // 6, 200))
        cta_height = max(30, min(height // 12, 50))
        
        return {
            'headline': {
                'text': 'Revolutionary AI Solution',
                'font_family': 'Arial',
                'font_size': headline_size,
                'color': '#2C3E50',
                'position': {'x': width // 20, 'y': height // 4},
                'dimensions': {'width': width * 0.9, 'height': headline_size * 1.2},
                'alignment': 'left'
            },
            'subheadline': {
                'text': 'Transform your business with cutting-edge technology',
                'font_family': 'Arial',
                'font_size': subheadline_size,
                'color': '#34495E',
                'position': {'x': width // 20, 'y': height // 2},
                'dimensions': {'width': width * 0.9, 'height': subheadline_size * 2.5},
                'alignment': 'left'
            },
            'cta_button': {
                'text': 'Get Started',
                'font_family': 'Arial',
                'font_size': max(14, subheadline_size - 4),
                'color': '#FFFFFF',
                'background_color': '#3498DB',
                'position': {'x': width // 20, 'y': int(height * 0.75)},
                'dimensions': {'width': cta_width, 'height': cta_height},
                'border_radius': 5
            },
            'logo': {
                'position': {'x': int(width * 0.8), 'y': height // 20},
                'dimensions': {'width': max(60, width // 15), 'height': max(30, height // 20)}
            }
        }
    
    def design_reviewer_agent(self, user_input: str, layout_spec: Dict[str, Any], background_description: str,
                        width: int, height: int, iteration: int = 1,
                        png_preview_b64: str = None) -> Dict[str, Any]:
        """
        Design Reviewer Agent: Reviews and provides feedback on the design using a PNG preview.
        """
        print(f"🔍 Design Reviewer Agent: Reviewing design (iteration {iteration})...")

        system_prompt = self.prompts['design_reviewer'].replace('{width}', str(width)).replace('{height}', str(height))
        messages = [SystemMessage(content=system_prompt)]

        # Đã thêm user_input vào đây để agent có thể đối chiếu
        content = [{"type": "text", "text": f"""Review this banner design (iteration {iteration}):

    Original User Request: "{user_input}"

    Dimensions: {width}x{height}px
    Background: {background_description}
    Layout specification:
    {json.dumps(layout_spec, indent=2)}

    Critically evaluate the design against the user request and visual quality rules."""}]

        if png_preview_b64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{png_preview_b64}"}
            })
            content.append({"type": "text", "text": "Above is the visual preview of the banner design."})

        messages.append(HumanMessage(content=content))

        try:
            response = self.llm.invoke(messages)
            feedback = self.parse_feedback(response.content)

            print(f"✅ Review completed: {len(feedback.get('issues', []))} issues found")
            return feedback

        except Exception as e:
            print(f"⚠️ Review error: {e}")
            return {
                'approved': iteration >= max_iterations, # Chỉ approve ở lần cuối nếu có lỗi
                'issues': [{'reason': f'Reviewer agent failed with error: {e}'}],
                'suggestions': []
            }
    
    def parse_feedback(self, response: str) -> Dict[str, Any]:
        """Parse structured JSON feedback from reviewer"""
        try:
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                feedback_json = response[start:end+1]
                feedback = json.loads(feedback_json)
                return feedback
        except Exception as e:
            print(f"⚠️ Parse feedback JSON error: {e}")

        # fallback nếu parse thất bại
        return {
            "approved": False,
            "issues": [],
            "suggestions": []
        }
    
        # THÊM CÁC HÀM MỚI NÀY VÀO BÊN TRONG CLASS BannerAgent

    def visual_asset_agent(self, user_input: str, theme: str, mood: str) -> str:
        """
        Visual Asset Agent: Creates a detailed prompt for a text-to-image model.
        """
        print("🖼️ Visual Asset Agent: Generating image prompt...")
        system_prompt = self.prompts['visual_asset_system_prompt']
        context_prompt = self.prompts['visual_asset_context_prompt'].format(
            user_input=user_input,
            theme=theme,
            mood=mood
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            image_prompt = response.content.strip().strip('"')
            print(f"✅ Image prompt generated: \"{image_prompt}\"")
            return image_prompt
        except Exception as e:
            print(f"⚠️ Visual Asset Agent error: {e}")
            return f"A minimalist, abstract background fitting a {theme} theme."


    def text_to_image_generation(self, prompt: str, width: int, height: int, image_name: str = "hero_image.png") -> str:
        """
        Calls DALL-E 3, downloads the image, resizes it for efficiency, and saves it.
        """
        print(f"🤖 Calling DALL-E 3 API with prompt: \"{prompt[:80]}...\"")
        
        from openai import OpenAI
        from PIL import Image
        import requests
        import io

        try:
            client = OpenAI()
            
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024", # Kích thước phổ biến của DALL-E 3
                quality="standard",
                n=1,
                response_format="url"
            )
            
            image_url = response.data[0].url
            print(f"✅ DALL-E 3 generated image URL: {image_url.split('?')[0]}") # In URL sạch
            
            # Tải ảnh từ URL
            image_response = requests.get(image_url)
            image_response.raise_for_status() # Báo lỗi nếu tải thất bại

            # --- BƯỚC TỐI ƯU HÓA MỚI ---
            print(f"🖼️ Resizing image to fit banner dimensions ({width}x{height})...")
            
            # Mở ảnh từ dữ liệu tải về
            img = Image.open(io.BytesIO(image_response.content))
            
            # Thay đổi kích thước ảnh một cách thông minh (giữ tỷ lệ)
            # Bằng cách này, chúng ta đảm bảo ảnh vừa khít với chiều rộng hoặc chiều cao
            # của banner mà không bị méo.
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            # Tạo một ảnh nền mới và dán ảnh đã resize vào giữa
            # Điều này xử lý trường hợp tỷ lệ ảnh DALL-E không khớp với banner
            final_img = Image.new("RGB", (width, height))
            paste_coords = ((width - img.width) // 2, (height - img.height) // 2)
            final_img.paste(img, paste_coords)
            # --- KẾT THÚC BƯỚC TỐI ƯU HÓA ---
            
            output_dir = "generated_images"
            os.makedirs(output_dir, exist_ok=True)
            image_path = os.path.join(output_dir, image_name)
            
            # Lưu ảnh đã được resize
            final_img.save(image_path, "PNG")
            
            print(f"✅ Image downloaded, resized, and saved to: {image_path}")
            return image_path

        except Exception as e:
            print(f"⚠️ DALL-E 3 process failed: {e}")
            # Fallback an toàn
            img = Image.new('RGB', (width, height), color = '#555555')
            d = ImageDraw.Draw(img)
            d.text((10,10), "API/Resize failed", fill=(255,255,255))
            fallback_path = os.path.join("generated_images", "fallback_image.png")
            img.save(fallback_path)
            return fallback_path


    def export_to_svg(self, layout: Dict[str, Any], composition: Dict[str, Any], width: int, height: int, logo_path: str) -> str:
        """
        Generate SVG with embedded Google Fonts for consistent rendering.
        Includes error handling for font fetching.
        """
        print("🎨 Generating SVG with embedded fonts...")
        
        # --- PHẦN 1: Tải và nhúng Google Fonts ---
        fonts_to_embed = {
            "Orbitron": "https://fonts.googleapis.com/css2?family=Orbitron:wght@700&display=swap",
            "Roboto": "https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap"
        }
        font_styles = ""
        try:
            # Thêm user-agent để giả lập trình duyệt, tránh bị Google chặn
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
            for font_name, url in fonts_to_embed.items():
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    font_styles += response.text
                    print(f"✅ Successfully fetched font: {font_name}")
                else:
                    print(f"⚠️ Failed to fetch font {font_name}. Status code: {response.status_code}")
        except ImportError:
            print("⚠️ 'requests' library not found. Cannot embed fonts. Please run 'pip install requests'.")
        except Exception as e:
            print(f"⚠️ An error occurred during font fetching: {e}")
        # --- Kết thúc Phần 1 ---

        # Bắt đầu chuỗi SVG
        svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
        
        # Thêm thẻ <defs> và <style> để chứa định nghĩa font và gradient
        svg += f'<defs><style>{font_styles}</style>'

        bg_struct = composition.get("background_structure", {})
        base_layer = bg_struct.get("base_layer", {"type": "solid", "colors": ["#FFFFFF"]})
        if base_layer.get("type") == "gradient" and len(base_layer.get("colors", [])) >= 2:
            colors = base_layer["colors"]
            svg += f'<linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="{colors[0]}"/><stop offset="100%" stop-color="{colors[1]}"/></linearGradient>'
            svg += '</defs>'
            svg += f'<rect width="{width}" height="{height}" fill="url(#bgGrad)"/>'
        else:
            color = base_layer.get("colors", ["#FFFFFF"])[0]
            svg += '</defs>'
            svg += f'<rect width="{width}" height="{height}" fill="{color}"/>'

        # 2. **VẼ HỌA TIẾT NỀN (OVERLAY_LAYER) - SỬ DỤNG LOGIC CHI TIẾT CỦA BẠN**
        overlay_layer = bg_struct.get("overlay_layer")
        if overlay_layer and overlay_layer.get("type") != "none":
            overlay_type = overlay_layer.get("type")
            color = overlay_layer.get("color", "#FFFFFF")
            opacity = overlay_layer.get("opacity", 0.1)
            
            pattern_svg = ""
            if overlay_type in ["grid", "circuitry"]:
                for i in range(0, width, 20):
                    pattern_svg += f'<line x1="{i}" y1="0" x2="{i}" y2="{height}" stroke="{color}" stroke-opacity="{opacity}" stroke-width="0.5"/>'
                for i in range(0, height, 20):
                    pattern_svg += f'<line x1="0" y1="{i}" x2="{width}" y2="{i}" stroke="{color}" stroke-opacity="{opacity}" stroke-width="0.5"/>'
            elif overlay_type in ["organic_shapes", "subtle_waves"]:
                for _ in range(15):
                    import random
                    x, y = random.randint(0, width), random.randint(0, height)
                    scale = random.uniform(0.5, 1.2)
                    pattern_svg += f'<path transform="translate({x}, {y}) scale({scale})" fill="{color}" fill-opacity="{opacity}" d="M15.1,3.1C14,1.2,12.3,0,10,0C7.7,0,6,1.2,4.9,3.1C3.8,5,3.8,7,4.9,8.9l-4,6.9C0.3,16.7,0,17.9,0,19c0,3.3,2.7,6,6,6 c1.1,0,2.3-0.3,3.1-0.9l6.9-4c1.9,1.1,3.9,1.1,5.8,0l6.9,4c0.8,0.6,2,0.9,3.1,0.9c3.3,0,6-2.7,6-6c0-1.1-0.3-2.3-0.9-3.1l-4-6.9 C26.2,7,26.2,5,25.1,3.1z"/>'
            
            svg += pattern_svg

        comp_type = composition.get("composition_type")
        hero_path = composition.get("hero_image_path")
        if hero_path and os.path.exists(hero_path):
            try:
                with open(hero_path, "rb") as img_file:
                    base64_img = base64.b64encode(img_file.read()).decode('utf-8')
                mime = guess_type(hero_path)[0] or 'image/png'
                
                if comp_type == "full_bleed":
                    svg += f'<image x="0" y="0" width="{width}" height="{height}" xlink:href="data:{mime};base64,{base64_img}" preserveAspectRatio="xMidYMid slice"/>'
                elif comp_type == "split_screen":
                    svg += f'<image x="0" y="0" width="{width * 0.5}" height="{height}" xlink:href="data:{mime};base64,{base64_img}" preserveAspectRatio="xMidYMid slice"/>'
            except Exception as e:
                print(f"⚠️ Hero image rendering error: {e}")

        # 4. Vẽ lớp phủ cho văn bản (Text Overlay)
        text_overlay = composition.get("text_overlay")
        if text_overlay and text_overlay.get("apply"):
            color = text_overlay.get("color", "#000000")
            opacity = text_overlay.get("opacity", 0.5)
            svg += f'<rect x="0" y="0" width="{width}" height="{height}" fill="{color}" fill-opacity="{opacity}"/>'    

        # --- PHẦN 2: Render Text với font đã được nhúng ---
        def render_text(element_name, default_font_size):
            if element_name not in layout or not layout.get(element_name): return ""
            elem = layout[element_name]
            text_content = elem.get('text', '')
            lines = text_content if isinstance(text_content, list) else [text_content]
            
            font_size = elem.get('font_size', default_font_size)
            x = elem.get('position', {}).get('x', 10)
            y = elem.get('position', {}).get('y', font_size)
            
            # Thêm font-weight và font-family dự phòng (sans-serif)
            font_weight = "700" if element_name == 'headline' else "400"
            font_family = elem.get("font_family", "Arial")
            
            text_svg = f'<text x="{x}" y="{y}" font-family="{font_family}, sans-serif" font-size="{font_size}" fill="{elem.get("color", "#FFFFFF")}" font-weight="{font_weight}">'
            for i, line in enumerate(lines):
                text_svg += f'<tspan x="{x}" dy="{ "1.2em" if i > 0 else 0 }">{line}</tspan>'
            text_svg += '</text>'
            return text_svg

        svg += render_text('headline', 28)
        svg += render_text('subheadline', 16)
        # --- Kết thúc Phần 2 ---

        # CTA Button
        if 'cta_button' in layout and layout.get('cta_button'):
            cta = layout['cta_button']
            pos, dims, font_size = cta.get('position', {}), cta.get('dimensions', {}), cta.get('font_size', 14)
            font_family = cta.get('font_family', 'Arial')
            
            svg += f'<rect x="{pos.get("x", 0)}" y="{pos.get("y", 0)}" width="{dims.get("width", 100)}" height="{dims.get("height", 40)}" rx="{cta.get("border_radius", 5)}" fill="{cta.get("background_color", "#007BFF")}"/>'
            text_x, text_y = pos.get('x', 0) + dims.get('width', 100) // 2, pos.get('y', 0) + dims.get('height', 40) // 2 + font_size // 3
            svg += f'<text x="{text_x}" y="{text_y}" font-family="{font_family}, sans-serif" font-size="{font_size}" fill="{cta.get("color", "#FFFFFF")}" text-anchor="middle" font-weight="700">{cta.get("text", "")}</text>'

        # Logo
        if logo_path and os.path.exists(logo_path) and 'logo' in layout and layout.get('logo'):
            try:
                with open(logo_path, "rb") as img_file:
                    base64_img = base64.b64encode(img_file.read()).decode('utf-8')
                mime = guess_type(logo_path)[0] or 'image/png'
                logo, pos, dims = layout['logo'], layout['logo'].get('position', {}), layout['logo'].get('dimensions', {})
                svg += f'<image x="{pos.get("x", 0)}" y="{pos.get("y", 0)}" width="{dims.get("width", 80)}" height="{dims.get("height", 30)}" xlink:href="data:{mime};base64,{base64_img}"/>'
            except Exception as e:
                print(f"⚠️ Logo rendering error: {e}")
        
        svg += '</svg>'
        print("✅ SVG generation complete with embedded fonts.")
        return svg


    def extract_logo_name_from_path(self, logo_path: str) -> str:
        """Extract a display name from logo file path"""
        if not logo_path:
            return "LOGO"
        
        # Get filename without extension
        filename = os.path.splitext(os.path.basename(logo_path))[0]
        
        # Handle common naming patterns
        if "ethic" in filename.lower():
            return "ETHIC AI"
        elif "ai" in filename.lower():
            return "AI"
        elif "_" in filename:
            # Split on underscore and capitalize
            parts = filename.split("_")
            return " ".join(part.upper() for part in parts if part.isalpha())
        else:
            return filename.upper()[:10]  # Limit length

    def export_to_figma_plugin(self, layout: Dict[str, Any], background_description: str, width: int, height: int) -> Dict[str, str]:
        """Generate complete Figma Plugin files"""
        
        # manifest.json
        manifest = {
            "name": "Banner Generator Plugin",
            "id": "banner-generator",
            "api": "1.0.0",
            "main": "code.js",
            "ui": "ui.html"
        }
        
        # ui.html
        ui_html = f'''<!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Banner Generator</title>
            <style>
                body {{ font-family: 'Inter', sans-serif; margin: 20px; }}
                .banner-preview {{ 
                    width: {width//2}px; 
                    height: {height//2}px; 
                    border: 1px solid #ccc; 
                    margin: 10px 0; 
                    transform-origin: top left;
                    transform: scale(0.5);
                }}
                button {{ 
                    background: #18A0FB; 
                    color: white; 
                    border: none; 
                    padding: 8px 16px; 
                    border-radius: 6px; 
                    cursor: pointer; 
                }}
            </style>
        </head>
        <body>
            <h2>Banner Generator</h2>
            <div class="banner-preview" id="preview"></div>
            <button onclick="createBanner()">Create Banner in Figma</button>
            
            <script>
                const layout = {json.dumps(layout, indent=2)};
                const dimensions = {{ width: {width}, height: {height} }};
                
                function createBanner() {{
                    parent.postMessage({{ pluginMessage: {{ type: 'create-banner', layout, dimensions }} }}, '*');
                }}
                
                // Preview rendering
                document.getElementById('preview').innerHTML = `
                    <div style="width: {width}px; height: {height}px; background: #f0f0f0; position: relative;">
                        <div style="position: absolute; left: {layout.get('headline', {}).get('position', {}).get('x', 0)}px; 
                                top: {layout.get('headline', {}).get('position', {}).get('y', 0)}px; 
                                font-size: {layout.get('headline', {}).get('size', 24)}px; 
                                color: {layout.get('headline', {}).get('color', '#000')};
                                font-family: {layout.get('headline', {}).get('font', 'Arial')};">
                            {layout.get('headline', {}).get('text', 'Headline')}
                        </div>
                    </div>
                `;
            </script>
        </body>
        </html>'''
        
        # code.js (Figma Plugin API)
        code_js = f'''// Figma Plugin Code
        figma.showUI(__html__, {{ width: 400, height: 300 }});

        figma.ui.onmessage = msg => {{
        if (msg.type === 'create-banner') {{
            const {{ layout, dimensions }} = msg;
            
            // Create frame for banner
            const frame = figma.createFrame();
            frame.name = "Generated Banner";
            frame.resize(dimensions.width, dimensions.height);
            frame.fills = [{{
            type: 'SOLID',
            color: {{ r: 0.94, g: 0.94, b: 0.94 }}
            }}];
            
            // Add headline
            if (layout.headline) {{
            const headline = figma.createText();
            headline.name = "Headline";
            headline.characters = layout.headline.text;
            headline.fontSize = layout.headline.size;
            headline.x = layout.headline.position.x;
            headline.y = layout.headline.position.y;
            
            // Convert hex color to RGB
            const color = hexToRgb(layout.headline.color);
            headline.fills = [{{
                type: 'SOLID',
                color: {{ r: color.r/255, g: color.g/255, b: color.b/255 }}
            }}];
            
            frame.appendChild(headline);
            }}
            
            // Add CTA button
            if (layout.cta) {{
            const button = figma.createRectangle();
            button.name = "CTA Button";
            button.resize(layout.cta.width, layout.cta.height);
            button.x = layout.cta.position.x;
            button.y = layout.cta.position.y;
            button.cornerRadius = layout.cta.border_radius;
            
            const bgColor = hexToRgb(layout.cta.background_color);
            button.fills = [{{
                type: 'SOLID',
                color: {{ r: bgColor.r/255, g: bgColor.g/255, b: bgColor.b/255 }}
            }}];
            
            // Add button text
            const buttonText = figma.createText();
            buttonText.name = "CTA Text";
            buttonText.characters = layout.cta.text;
            buttonText.fontSize = layout.cta.size;
            buttonText.x = layout.cta.position.x + layout.cta.width/2;
            buttonText.y = layout.cta.position.y + layout.cta.height/2;
            buttonText.textAlignHorizontal = "CENTER";
            buttonText.textAlignVertical = "CENTER";
            
            const textColor = hexToRgb(layout.cta.color);
            buttonText.fills = [{{
                type: 'SOLID',
                color: {{ r: textColor.r/255, g: textColor.g/255, b: textColor.b/255 }}
            }}];
            
            frame.appendChild(button);
            frame.appendChild(buttonText);
            }}
            
            // Select and zoom to the created frame
            figma.currentPage.selection = [frame];
            figma.viewport.scrollAndZoomIntoView([frame]);
            
            figma.closePlugin("Banner created successfully!");
        }}
        }};

        function hexToRgb(hex) {{
        const result = /^#?([a-f\\d]{{2}})([a-f\\d]{{2}})([a-f\\d]{{2}})$/i.exec(hex);
        return result ? {{
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        }} : {{ r: 0, g: 0, b: 0 }};
        }}'''
        
        return {
            "manifest.json": json.dumps(manifest, indent=2),
            "ui.html": ui_html,
            "code.js": code_js
        }



    def create_banner(self, user_input: str, logo_path: str = None,
                   width: int = 1200, height: int = 628, max_iterations: int = 3,
                   output_format: str = "json") -> str:
        """
        Main method using the Art Director architecture to create a banner.
        """
        print(f"🚀 Starting Banner Creation Process (Art Director Mode)...")
        print(f"📏 Dimensions: {width}x{height}px")

        try:
            # Step 1: Strategic Planning
            objectives = self.strategist_agent(user_input, logo_path)
            theme = objectives.get("theme", "general")
            mood = objectives.get("mood", "neutral")
            color_palette = objectives.get("color_palette", {})
            print(f"🎯 Strategist Agent: Theme='{theme}', Colors={color_palette}")

            # Step 2: Visual Asset Creation
            hero_image_prompt = self.visual_asset_agent(user_input, theme, mood)
            hero_image_path = self.text_to_image_generation(hero_image_prompt, width, height)

            # Step 3: Composition Design (using the upgraded background_designer_agent)
            composition_structure = self.background_designer_agent(
                theme, mood, color_palette, hero_image_path
            )
            print(f"🎨 Composition Director: Generated structure: {composition_structure}")

            # Step 4: Foreground Design
            layout_spec = self.foreground_designer_agent(user_input, objectives, width, height)
            
            if 'color_palette' not in layout_spec:
                 layout_spec['color_palette'] = color_palette

            # Step 5: Iterative Design Review and Refinement
            current_layout = layout_spec
            final_svg_content = ""

            for iteration in range(1, max_iterations + 1):
                print(f"\n🔄 Design Iteration {iteration}")

                svg_content = self.export_to_svg(current_layout, composition_structure, width, height, logo_path)
                final_svg_content = svg_content

                try:
                    png_bytes = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'))
                    png_preview_b64 = base64.b64encode(png_bytes).decode('utf-8')
                except Exception as convert_error:
                    print(f"⚠️ Error converting SVG to PNG: {convert_error}. Approving to avoid loop.")
                    feedback = {'approved': True}
                else:
                    background_info_for_reviewer = json.dumps(composition_structure)
                    feedback = self.design_reviewer_agent(
                        user_input, current_layout, background_info_for_reviewer, width, height, iteration, png_preview_b64
                    )

                if feedback.get('approved', False):
                    print(f"✅ Design approved after {iteration} iteration(s)")
                    break
                
                if iteration == max_iterations:
                    print(f"✅ Reached max iterations. Using current design.")
                    break

                if feedback.get('issues'):
                    current_layout = self.refine_layout(current_layout, feedback)
                    print(f"🔧 Applied {len(feedback['issues'])} refinements")

            print("\n🎉 Banner creation completed!")

            if output_format == "svg":
                return final_svg_content
            else:
                final_result = {
                    'objectives': objectives,
                    'composition_structure': composition_structure,
                    'layout': current_layout,
                    'dimensions': {'width': width, 'height': height},
                    'iterations': iteration
                }
                return json.dumps(final_result, indent=2, ensure_ascii=False)

        except Exception as e:
            import traceback
            print(f"⌫ An unexpected error occurred in banner creation: {str(e)}")
            traceback.print_exc()
            return json.dumps({"error": f"Unexpected error: {str(e)}"})

    
    def refine_layout(self, layout_spec: Dict[str, Any], feedback: Dict[str, Any]) -> Dict[str, Any]:
        refined = json.loads(json.dumps(layout_spec))  # Deep copy

        for issue in feedback.get("issues", []):
            elem = issue.get("element")
            if elem not in refined:
                continue

            action = issue.get("action")
            params = issue.get("parameters", {})

            if action == "reposition":
                if "x" in params:
                    refined[elem]["position"]["x"] = params["x"]
                if "y" in params:
                    refined[elem]["position"]["y"] = params["y"]
            elif action == "recolor":
                if "color" in params:
                    refined[elem]["color"] = params["color"]
                if "background_color" in params:
                    refined[elem]["background_color"] = params["background_color"]
            elif action == "retext":
                if "text" in params:
                    refined[elem]["text"] = params["text"]
            elif action == "resize":
                # Cho phép resize cả dimensions và font_size
                if "width" in params:
                    refined[elem].setdefault("dimensions", {})["width"] = params["width"]
                if "height" in params:
                    refined[elem].setdefault("dimensions", {})["height"] = params["height"]
                if "font_size" in params:
                    refined[elem]["font_size"] = params["font_size"]
            # Giữ lại stylechange cho các trường hợp khác
            elif action == "stylechange":
                if "font_family" in params:
                    refined[elem]["font_family"] = params["font_family"]
                if "border_radius" in params:
                    refined[elem]["border_radius"] = params["border_radius"]

        return refined


def main():
    """Example usage"""
    # Initialize the agent
    agent = BannerAgent(model_name="gpt-5-nano")
    
    # Example banner request
    user_request = "Create a banner for a tech startup launching a new AI product. The banner should be modern, professional, and appeal to business executives."
    logo_path = "./logos/example_logo.png"  # Optional
    
    # Create banner
    result = agent.create_banner(
        user_input=user_request,
        logo_path=logo_path if os.path.exists(logo_path) else None,
        width=1200,
        height=628,
        max_iterations=3
    )
    
    print("\n📄 Final Banner Specification:")
    print(result)

if __name__ == "__main__":
    main()