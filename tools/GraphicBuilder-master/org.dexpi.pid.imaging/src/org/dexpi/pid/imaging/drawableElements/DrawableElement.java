package org.dexpi.pid.imaging.drawableElements;

import java.awt.Color;

/**
 * A simple geometric element, that can be drawn by the GraphicFactory.
 * 
 * @author El Pulpo
 *
 */
public class DrawableElement {

	int lineNumber;
	float lineWeight;
	Color color;
	DrawableElement.LineType lineType;

	public LineType getLineType() {
		return lineType;
	}

	public void setLineType(LineType lineType) {
		this.lineType = lineType;
	}

	/**
	 * sets the color
	 * 
	 * @param color
	 *            the color
	 */
	public void setColor(Color color) {
		this.color = color;
	}

	/**
	 * 
	 * @return the color
	 */
	public Color getColor() {
		return this.color;
	}

	/**
	 * sets the line weight
	 * 
	 * @param lineWeight
	 *            the line weight
	 */
	public void setLineWeight(float lineWeight) {
		this.lineWeight = lineWeight;
	}

	/**
	 * 
	 * @return the line weight
	 */
	public float getLineWeight() {
		return this.lineWeight;
	}

	/**
	 * sets the line number
	 * 
	 * @param lineNumber
	 *            the line number
	 */
	public void setLineNumber(int lineNumber) {
		this.lineNumber = lineNumber;
	}

	/**
	 * 
	 * @return the line number
	 */
	public int getLineNumber() {
		return this.lineNumber;
	}


	public enum LineType {
		SOLID("Solid", 0, new float[]{0}),
		DOTTED("Dotted", 1, new float[]{1}),
		DASHED("Dashed", 2, new float[]{4}),
		LONG_DASH("Long Dash", 3, new float[]{8}),
		LONG_DASH_SHORT_DASH("Long Dash + Short Dash, CenterLine", 4, new float[]{8, 4}),
		SHORT_DASH("Short Dash", 5, new float[]{2}),
		LONG_DASH_SHORT_DASH_SHORT_DASH("Long Dash + Short Dash + Short Dash", 6, new float[]{8, 2, 2}),
		DASH_SHORT_DASH("Dash + Short Dash", 7, new float[]{4, 2});

		private final String value;
		private final int index;
		private final float[] svgStyleMultiplier;

		LineType(String value, int index, float[] svgStyleMultiplier) {
			this.value = value;
			this.index = index;
			this.svgStyleMultiplier = svgStyleMultiplier;
		}

		public static LineType fromIndex(int index) {
			for (LineType lineType : LineType.values()) {
				if (lineType.index == index) {
					return lineType;
				}
			}
			return SOLID;
		}

		public static LineType fromValue(String value) {
			for (LineType lineType : LineType.values()) {
				if (lineType.value.equals((value))) {
					return lineType;
				}
			}
			return SOLID;
		}

		/**
		 * Gets the svg style for the stroke-dasharray attribute
		 *
		 * @return Value for stroke-dasharray attribute
		 */
		public String getSvgStyle(double strokeWidth) {
			StringBuilder builder = new StringBuilder();
			for (float v : this.svgStyleMultiplier) {
				builder.append(strokeWidth * v);
				builder.append(" ");
			}
			return builder.toString();
		}
	}
}
