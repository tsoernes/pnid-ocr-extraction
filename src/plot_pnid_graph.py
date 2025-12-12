"""
Interactive P&ID Graph Visualization with Background Image.

This script loads the extracted P&ID graph from JSON and displays it
as an interactive network graph with the original diagram as background.
Nodes can be freely moved/dragged by the user.
"""

import base64
import json
from pathlib import Path

from pyvis.network import Network


def load_image_as_base64(image_path: str) -> str:
    """Load an image and convert to base64 data URI."""
    with open(image_path, "rb") as f:
        data = f.read()
    ext = Path(image_path).suffix.lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{base64.b64encode(data).decode()}"


def load_pnid_data(json_path: str) -> dict:
    """Load P&ID graph data from JSON file."""
    with open(json_path, "r") as f:
        return json.load(f)


def get_category_color(category: str) -> str:
    """Return a color based on component category."""
    colors = {
        "Vessel": "#4CAF50",  # Green
        "Heat Exchanger": "#FF9800",  # Orange
        "Separator": "#2196F3",  # Blue
        "Pump": "#9C27B0",  # Purple
        "Valve": "#F44336",  # Red
        "source": "#9E9E9E",  # Gray (for source nodes)
        "sink": "#607D8B",  # Blue Gray (for sink nodes)
    }
    return colors.get(category, "#795548")  # Brown default


def get_node_shape(category: str) -> str:
    """Return a shape based on component category."""
    shapes = {
        "Vessel": "ellipse",
        "Heat Exchanger": "box",
        "Separator": "diamond",
        "source": "triangle",
        "sink": "triangleDown",
    }
    return shapes.get(category, "dot")


def create_interactive_graph(
    json_path: str, image_path: str, output_path: str = "pnid_graph.html"
) -> None:
    """
    Create an interactive graph visualization with background image.

    Args:
        json_path: Path to the P&ID JSON file
        image_path: Path to the background image
        output_path: Path for the output HTML file
    """
    # Load data
    data = load_pnid_data(json_path)

    # Handle both old format (direct) and new format (nested in 'output')
    if "output" in data:
        components = {c["id"]: c for c in data["output"]["components"]}
        pipes = data["output"]["pipes"]
    else:
        components = {c["id"]: c for c in data["components"]}
        pipes = data["pipes"]

    # Load image to get dimensions for coordinate transformation
    from PIL import Image

    img = Image.open(image_path)
    img_width, img_height = img.size

    # Function to convert image coordinates to vis.js coordinates
    # Vis.js uses center origin (0,0) with Y-axis pointing down (same as image)
    # Image uses top-left origin with pixel coordinates
    def transform_coords(x, y):
        # Center the coordinates (both image and vis.js use Y-down)
        # Scale to match typical vis.js canvas size (~1000 units)
        scale = 1000 / max(img_width, img_height)
        vis_x = (x - img_width / 2) * scale
        vis_y = (y - img_height / 2) * scale  # No flip - both use Y-down
        return vis_x, vis_y

    # Create network with physics enabled for draggable nodes
    net = Network(
        height="900px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#000000",
        directed=True,
        notebook=False,
        select_menu=False,
        filter_menu=False,
    )

    # Configure physics - disabled by default for free node movement
    net.set_options("""
    {
        "physics": {
            "enabled": false
        },
        "interaction": {
            "dragNodes": true,
            "dragView": true,
            "zoomView": true,
            "hover": true,
            "tooltipDelay": 100
        },
        "nodes": {
            "font": {
                "size": 14,
                "face": "arial",
                "strokeWidth": 3,
                "strokeColor": "#ffffff"
            },
            "borderWidth": 2,
            "shadow": true
        },
        "edges": {
            "arrows": {
                "to": {
                    "enabled": true,
                    "scaleFactor": 0.8
                }
            },
            "color": {
                "inherit": false,
                "color": "#333333",
                "highlight": "#ff0000"
            },
            "font": {
                "size": 10,
                "align": "middle",
                "strokeWidth": 2,
                "strokeColor": "#ffffff"
            },
            "smooth": {
                "enabled": true,
                "type": "curvedCW",
                "roundness": 0.2
            },
            "width": 2,
            "shadow": true
        }
    }
    """)

    # Build per-pipe unique inlet / outlet node ids based on label and target/source
    # Treat any pipe endpoint that is not a known component id as a distinct inlet/outlet node
    augmented_pipes: list[dict[str, Any]] = []
    for idx, pipe in enumerate(pipes):
        src = pipe["source"]
        tgt = pipe["target"]
        label = pipe.get("label", "")
        base_label = label.replace(" ", "").replace("°", "deg").replace(",", "")

        # Per-pipe unique inlet nodes: source not a known component
        if src not in components:
            src = f"inlet_{base_label}_{tgt}_{idx}"

        # Per-pipe unique outlet nodes: target not a known component
        if tgt not in components:
            tgt = f"outlet_{base_label}_{pipe['source']}_{idx}"

        new_pipe: dict[str, Any] = dict(pipe)
        new_pipe["source_node"] = src
        new_pipe["target_node"] = tgt
        # Store original stream info for nicer inlet/outlet labels
        new_pipe["__stream_label"] = label
        new_pipe["__stream_description"] = pipe.get("description", "")
        new_pipe["__orig_source"] = pipe["source"]
        new_pipe["__orig_target"] = pipe["target"]
        augmented_pipes.append(new_pipe)

    pipes = augmented_pipes

    # Collect all unique node IDs from pipes (using synthesized ids)
    all_node_ids = set()
    for pipe in pipes:
        all_node_ids.add(pipe["source_node"])
        all_node_ids.add(pipe["target_node"])

    # Add component nodes with actual x,y coordinates
    for node_id in all_node_ids:
        if node_id in components:
            comp = components[node_id]
            category = comp.get("category", "Unknown")
            color = get_category_color(category)
            shape = get_node_shape(category)

            # Get coordinates from extraction
            x = comp.get("x", 0)
            y = comp.get("y", 0)

            title = (
                f"<b>{comp['label']}</b><br>"
                f"Category: {category}<br>"
                f"Position: ({x:.1f}, {y:.1f})<br>"
                f"{comp.get('description', '')}"
            )

            # Transform coordinates to vis.js space
            vis_x, vis_y = transform_coords(x, y)

            net.add_node(
                node_id,
                label=comp["label"],
                title=title,
                color=color,
                shape=shape,
                size=30,
                x=vis_x,
                y=vis_y,
                physics=False,  # Use fixed positions from extraction
            )
        else:
            # Source or sink nodes (not in components list)
            # Try to find position from pipes (using synthesized ids)
            x = 0
            y = 0
            for pipe in pipes:
                if pipe["source_node"] == node_id or pipe["target_node"] == node_id:
                    x = pipe.get("x", 0)
                    y = pipe.get("y", 0)
                    break

            # Classify synthesized inlet/outlet vs other synthetic nodes
            if node_id.startswith("inlet_"):
                # Node id: inlet_<baseLabel>_<targetId>_<idx>
                # Recover a meaningful label from any pipe that uses this node_id
                stream_label = node_id
                target_id = ""
                for pipe in pipes:
                    if pipe["source_node"] == node_id:
                        # Prefer description as the human-friendly stream name if available
                        stream_label = (
                            pipe.get("__stream_description")
                            or pipe.get("__stream_label")
                            or stream_label
                        )
                        target_id = pipe.get("__orig_target", "")
                        break
                nice_stream = stream_label.replace("deg", "°")
                # Node label: stream only, e.g. "Malt, Corn, Water at 15°C"
                label = nice_stream
                color = get_category_color("source")
                shape = get_node_shape("source")
                title = (
                    f"<b>Inlet</b><br>"
                    f"Stream: {nice_stream}<br>"
                    f"To: {target_id or 'unknown'}<br>"
                    f"Position: ({x:.1f}, {y:.1f})"
                )
            elif node_id.startswith("outlet_"):
                # Node id: outlet_<baseLabel>_<sourceId>_<idx>
                stream_label = node_id
                source_id = ""
                for pipe in pipes:
                    if pipe["target_node"] == node_id:
                        # Prefer description as the human-friendly stream name if available
                        stream_label = (
                            pipe.get("__stream_description")
                            or pipe.get("__stream_label")
                            or stream_label
                        )
                        source_id = pipe.get("__orig_source", "")
                        break
                nice_stream = stream_label.replace("deg", "°")
                # Node label: "<stream> ← <source>"
                if source_id:
                    label = f"{nice_stream} \u2190 {source_id}"
                else:
                    label = nice_stream
                color = get_category_color("sink")
                shape = get_node_shape("sink")
                title = (
                    f"<b>Outlet</b><br>"
                    f"Stream: {nice_stream}<br>"
                    f"From: {source_id or 'unknown'}<br>"
                    f"Position: ({x:.1f}, {y:.1f})"
                )
            else:
                # Fallback for any other synthetic node ids
                label = node_id
                color = "#795548"
                shape = "dot"
                title = f"{node_id}<br>Position: ({x:.1f}, {y:.1f})"

            # Transform coordinates to vis.js space
            vis_x, vis_y = transform_coords(x, y)

            net.add_node(
                node_id,
                label=label,
                title=title,
                color=color,
                shape=shape,
                size=20,
                x=vis_x,
                y=vis_y,
                physics=False,
            )

    # Add edges (pipes) with position information
    for pipe in pipes:
        x = pipe.get("x", 0)
        y = pipe.get("y", 0)
        edge_title = (
            f"<b>{pipe['label']}</b><br>"
            f"Position: ({x:.1f}, {y:.1f})<br>"
            f"{pipe.get('description', '')}"
        )
        net.add_edge(
            pipe["source_node"],
            pipe["target_node"],
            label=pipe["label"],
            title=edge_title,
        )

    # Generate HTML
    net.write_html(output_path)

    # Load and modify HTML to add background image
    image_data_uri = load_image_as_base64(image_path)

    with open(output_path, "r") as f:
        html_content = f.read()

    # Add custom CSS for background image
    background_css = f"""
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
        #mynetwork {{
            background-image: url('{image_data_uri}');
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
            border: 2px solid #ccc;
        }}
        .legend {{
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            font-family: Arial, sans-serif;
            font-size: 12px;
            z-index: 1000;
        }}
        .legend h4 {{
            margin: 0 0 10px 0;
            font-size: 14px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 5px 0;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            margin-right: 8px;
            border-radius: 3px;
        }}
        .controls {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            font-family: Arial, sans-serif;
            z-index: 1000;
        }}
        .info {{
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 10px 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            font-family: Arial, sans-serif;
            font-size: 12px;
            z-index: 1000;
            color: #2196F3;
            font-weight: bold;
        }}
        .controls h4 {{
            margin: 0 0 10px 0;
            font-size: 14px;
        }}
        .controls button {{
            display: block;
            width: 100%;
            margin: 5px 0;
            padding: 8px 12px;
            border: none;
            border-radius: 4px;
            background: #2196F3;
            color: white;
            cursor: pointer;
            font-size: 12px;
        }}
        .controls button:hover {{
            background: #1976D2;
        }}
        .controls label {{
            display: block;
            margin: 10px 0 5px 0;
        }}
        .controls input[type="range"] {{
            width: 100%;
        }}
    </style>
    """

    # Add info banner and legend HTML
    info_html = """
    <div class="info">
        ℹ️ Node positions from AI-extracted coordinates
    </div>
    """

    legend_html = """
    <div class="legend">
        <h4>Legend</h4>
        <div class="legend-item">
            <div class="legend-color" style="background: #4CAF50;"></div>
            <span>Vessel</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #FF9800;"></div>
            <span>Heat Exchanger</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #2196F3;"></div>
            <span>Separator</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #9E9E9E;"></div>
            <span>Source</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #607D8B;"></div>
            <span>Sink</span>
        </div>
    </div>

    <div class="controls">
        <h4>Controls</h4>
        <button onclick="togglePhysics()">Toggle Physics</button>
        <button onclick="stabilize()">Stabilize Layout</button>
        <label>Background Opacity:</label>
        <input type="range" min="0" max="100" value="30" onchange="setOpacity(this.value)">
    </div>
    """

    controls_html = """
    <script>
        var physicsEnabled = true;

        function togglePhysics() {
            physicsEnabled = !physicsEnabled;
            network.setOptions({ physics: { enabled: physicsEnabled } });
        }

        function stabilize() {
            network.stabilize(100);
        }

        function setOpacity(value) {
            var opacity = value / 100;
            var networkDiv = document.getElementById('mynetwork');
            // Create a semi-transparent overlay effect
            networkDiv.style.backgroundImage =
                'linear-gradient(rgba(255,255,255,' + (1-opacity) + '), rgba(255,255,255,' + (1-opacity) + ')), ' +
                networkDiv.style.backgroundImage.split('), ').pop();
        }

        // Set initial opacity
        window.onload = function() {
            setTimeout(function() {
                setOpacity(30);
            }, 100);
        };
    </script>
    """

    # Insert CSS after <head>
    html_content = html_content.replace("<head>", "<head>" + background_css)

    # Insert info banner, legend and controls before </body>
    html_content = html_content.replace(
        "</body>", info_html + legend_html + controls_html + "</body>"
    )

    # Write modified HTML
    with open(output_path, "w") as f:
        f.write(html_content)

    print(f"Interactive graph saved to: {output_path}")
    print("Open the HTML file in a browser to view and interact with the graph.")
    print("\nFeatures:")
    print("  - Drag nodes to reposition them")
    print("  - Scroll to zoom in/out")
    print("  - Click and drag background to pan")
    print("  - Hover over nodes/edges for details")
    print("  - Use controls to toggle physics and adjust background opacity")


def main():
    """Main entry point."""
    # Define paths
    base_dir = Path(__file__).parent.parent
    json_path = base_dir / "data" / "output" / "pnid_gemini.json"
    image_path = base_dir / "data" / "input" / "brewery.jpg"
    output_path = base_dir / "data" / "output" / "pnid_graph.html"

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create the interactive graph
    create_interactive_graph(str(json_path), str(image_path), str(output_path))


if __name__ == "__main__":
    main()
