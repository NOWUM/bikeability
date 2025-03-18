import numpy as np
from plotly.express.colors import sample_colorscale
import pandas as pd
import geopandas as gpd
from shapely import wkt, Polygon
from shapely.ops import transform
import pydeck as pdk


def create_values(
        min_value: float,
        max_value: float) -> list[float]:  

    vals = np.arange(
        start=min_value,
        stop=max_value+0.01,
        step=0.01)

    vals = np.round(vals, decimals=2)

    return vals


def create_values_colorscale(
        values: list[float],
        colorscale: str = "Viridis"):

    normed_vals = values / (max(values) + 0.01)

    colorscale = sample_colorscale(
        colorscale=colorscale,
        samplepoints=normed_vals)

    return colorscale


def convert_plotly_to_rgb(
        plotly_str: str):
    
    color = plotly_str.removeprefix("rgb(")
    color = color.removesuffix(")")

    color = color.split(", ")
    color = [int(_) for _ in color]

    return color


def get_color_dict(
        min_value: float,
        max_value: float,
        colorscale: str):
    
    values = create_values(min_value=min_value, max_value=max_value)

    colorscale = create_values_colorscale(
        values=values,
        colorscale=colorscale)

    for i, color in enumerate(colorscale):

        colorscale[i] = convert_plotly_to_rgb(color)


    return dict(zip(values, colorscale))


def add_color_to_data(
        data: pd.DataFrame,
        min_value: float,
        max_value: float,
        value_col: str = "value",
        colorscale: str = "Viridis",
        color_dict: dict | None = None) -> pd.DataFrame:
    """
    Adds color column to given data.

    Parameters:
    -------------
    data: pd.DataFrame
        The data to add color to.

    min_value: float
        Minimum value to use for colorscale.

    max_value: float
        Maximum value to use for colorscale.

    value_col: str = "value"
        Value column to use for scaling.

    colorscale: str = "Plotly3"
        Plotly colorscale to use.

    color_dict: dict[str, list[int, int, int]]
        Dictionary to containing pairs of value: [r, g, b]
        to use as colorscale. Will overwrite "colorscale"
        parameter.
    """

    if not color_dict:
        color_dict = get_color_dict(
        min_value=min_value,
        max_value=max_value,
        colorscale=colorscale)

    data["adjusted_value"] = data[value_col].copy()
    data.loc[data["adjusted_value"] > max_value, "adjusted_value"] = max_value
    data.loc[data["adjusted_value"] < min_value, "adjusted_value"] = min_value

    data["color"] = data["adjusted_value"].round(2).map(color_dict)

    data.drop(columns="adjusted_value", inplace=True)

    return data


def create_viewstate(city):
    """
    Creates viewstate
    """
    cityhalls = pd.read_csv(f"../input/cityhalls.csv")
    
    if city == "Münster":
        city = "Muenster"
    elif city == "München":
        city = "Muenchen"
    
    cityhall = cityhalls[cityhalls.city == city]
    
    latitude=cityhall.iloc[0]["lat"]
    longitude=cityhall.iloc[0]["lon"]
    
    viewstate = pdk.ViewState(
        latitude=latitude,
        longitude=longitude,
        zoom=11,
        pitch=0)

    return viewstate

def flip(x,y):
    return y, x

def create_poylgon_pydeck(
        city: str,
        data: pd.DataFrame,
        tooltip: dict[str, str] | None = None) -> pdk.Deck:
    """
    Creates pydeck with PathLayer

    Parameters:
    -------------
    data: pd.DataFrame
        The data to create the pydeck for

    tooltip: dict[str, str]
        The tooltip to display on the pydeck
    """

    layer = pdk.Layer(
        type="PolygonLayer",
        data=data,
        pickable=True,
        filled=True,
        get_fill_color="color",
        get_line_color=[255, 255, 255],
        get_polygon="geom")

    viewstate = create_viewstate(city)

    deck = pdk.Deck(
        layers=[layer],
        map_style = "light",
        initial_view_state=viewstate,
        tooltip=tooltip)

    return deck

def vis_polygon():
    p = ([ [ 7.43669, 51.50911 ], [ 7.43136, 51.5093 ], [ 7.43064, 51.50933 ], 
          [ 7.42511, 51.51186 ], [ 7.42422, 51.51175 ], [ 7.42417, 51.51178 ], 
          [ 7.42331, 51.51167 ], [ 7.42181, 51.50983 ], [ 7.42019, 51.50208 ], 
          [ 7.40189, 51.50178 ], [ 7.39533, 51.50275 ], [ 7.39542, 51.50336 ],
          [ 7.39633, 51.50842 ], [ 7.39686, 51.50895 ], [ 7.39992, 51.50969 ], 
          [ 7.40067, 51.50989 ], [ 7.40722, 51.51155 ], [ 7.40914, 51.51203 ], 
          [ 7.41597, 51.51311 ], [ 7.41697, 51.51322 ], [ 7.41825, 51.514 ], 
          [ 7.41756, 51.51583 ], [ 7.41983, 51.51714 ], [ 7.42494, 51.52005 ], 
          [ 7.43014, 51.52303 ], [ 7.43447, 51.51981 ], [ 7.44114, 51.52125 ], 
          [ 7.44256, 51.52156 ], [ 7.44703, 51.5252 ], [ 7.44706, 51.5252 ],
          [ 7.44853, 51.5255 ], [ 7.45144, 51.52605 ], [ 7.45519, 51.53106 ], 
          [ 7.45456, 51.53472 ], [ 7.45733, 51.53539 ], [ 7.46192, 51.5365 ], 
          [ 7.47728, 51.53589 ], [ 7.47747, 51.53611 ], [ 7.48103, 51.54044 ], 
          [ 7.48253, 51.54081 ], [ 7.49086, 51.54181 ], [ 7.49489, 51.5385 ], 
          [ 7.50364, 51.53672 ], [ 7.50436, 51.53658 ], [ 7.50433, 51.53583 ], 
          [ 7.50433, 51.53525 ], [ 7.50433, 51.53519 ], [ 7.50064, 51.53294 ], 
          [ 7.49331, 51.53255 ], [ 7.48578, 51.52394 ], [ 7.48794, 51.52208 ], 
          [ 7.50853, 51.52647 ], [ 7.50975, 51.52628 ], [ 7.51269, 51.52581 ], 
          [ 7.51339, 51.5257 ], [ 7.53514, 51.53308 ], [ 7.53875, 51.53431 ], 
          [ 7.54833, 51.53756 ], [ 7.55419, 51.53794 ], [ 7.55567, 51.53575 ], 
          [ 7.55914, 51.53058 ], [ 7.56497, 51.53008 ], [ 7.56636, 51.52372 ], 
          [ 7.56694, 51.52106 ], [ 7.56697, 51.52092 ], [ 7.57644, 51.51989 ], 
          [ 7.57711, 51.51669 ], [ 7.56897, 51.51266 ], [ 7.56675, 51.51 ], 
          [ 7.56594, 51.50903 ], [ 7.5725, 51.49833 ], [ 7.573, 51.49753 ], 
          [ 7.56261, 51.49166 ], [ 7.56989, 51.49022 ], [ 7.56997, 51.48983 ], 
          [ 7.57053, 51.48703 ], [ 7.56753, 51.48294 ], [ 7.56314, 51.48342 ], 
          [ 7.56311, 51.48336 ], [ 7.56158, 51.47933 ], [ 7.55861, 51.47797 ], 
          [ 7.5535, 51.47758 ], [ 7.54956, 51.48011 ], [ 7.54917, 51.48036 ], 
          [ 7.54108, 51.47814 ], [ 7.53992, 51.47744 ], [ 7.53811, 51.47633 ], 
          [ 7.5395, 51.4733 ], [ 7.54019, 51.47175 ], [ 7.53283, 51.46953 ], 
          [ 7.5315, 51.4707 ], [ 7.52494, 51.47647 ], [ 7.52869, 51.47964 ],
          [ 7.52617, 51.48158 ], [ 7.52508, 51.48242 ], [ 7.51778, 51.48294 ], 
          [ 7.51528, 51.47989 ], [ 7.51403, 51.47839 ], [ 7.52039, 51.4692 ], 
          [ 7.51528, 51.46878 ], [ 7.50886, 51.47661 ], [ 7.50642, 51.47766 ], 
          [ 7.50236, 51.47942 ], [ 7.49792, 51.47672 ], [ 7.50042, 51.47575 ], 
          [ 7.50153, 51.4753 ], [ 7.50281, 51.46706 ], [ 7.50058, 51.46572 ], 
          [ 7.48781, 51.46186 ], [ 7.4865, 51.46147 ], [ 7.47261, 51.45728 ], 
          [ 7.46683, 51.46053 ], [ 7.46242, 51.45872 ], [ 7.46236, 51.45644 ], 
          [ 7.46883, 51.45136 ], [ 7.47019, 51.44722 ], [ 7.46361, 51.44636 ], 
          [ 7.45125, 51.44967 ], [ 7.44575, 51.45475 ], [ 7.44122, 51.45892 ], 
          [ 7.44225, 51.45967 ], [ 7.44494, 51.46161 ], [ 7.45081, 51.46294 ], 
          [ 7.45236, 51.46658 ], [ 7.45681, 51.46931 ], [ 7.45539, 51.47114 ], 
          [ 7.43706, 51.469 ], [ 7.43864, 51.47495 ], [ 7.43178, 51.47533 ], 
          [ 7.42914, 51.47547 ], [ 7.42689, 51.47275 ], [ 7.42253, 51.47417 ], 
          [ 7.43, 51.48095 ], [ 7.42939, 51.48644 ], [ 7.43506, 51.48745 ], 
          [ 7.43672, 51.48775 ], [ 7.44253, 51.48589 ], [ 7.44392, 51.48222 ], 
          [ 7.45408, 51.47892 ], [ 7.45714, 51.48531 ], [ 7.46083, 51.48664 ], 
          [ 7.46428, 51.48736 ], [ 7.46628, 51.48778 ], [ 7.47286, 51.48917 ], 
          [ 7.47553, 51.48972 ], [ 7.47917, 51.48922 ], [ 7.4815, 51.49044 ], 
          [ 7.48286, 51.49103 ], [ 7.48814, 51.49081 ], [ 7.49675, 51.49044 ], 
          [ 7.50203, 51.49725 ], [ 7.50178, 51.49842 ], [ 7.50136, 51.50047 ], 
          [ 7.49603, 51.50261 ], [ 7.49542, 51.50256 ], [ 7.49403, 51.50008 ], 
          [ 7.48594, 51.49786 ], [ 7.48297, 51.50128 ], [ 7.47953, 51.50522 ], 
          [ 7.46925, 51.5045 ], [ 7.45094, 51.50319 ], [ 7.44664, 51.50733 ], 
          [ 7.43933, 51.50786 ], [ 7.43792, 51.50972 ], [ 7.43708, 51.50989 ], 
          [ 7.43669, 51.50911 ], [ 7.46397, 51.48392 ], [ 7.46369, 51.48386 ], 
          [ 7.46211, 51.47794 ], [ 7.46342, 51.47153 ], [ 7.46397, 51.47147 ], 
          [ 7.46917, 51.46689 ], [ 7.47553, 51.46775 ], [ 7.48658, 51.46925 ], 
          [ 7.48825, 51.46947 ], [ 7.489, 51.47208 ], [ 7.49061, 51.4777 ], 
          [ 7.49433, 51.48086 ], [ 7.49225, 51.485 ], [ 7.48644, 51.48778 ], 
          [ 7.48281, 51.48828 ], [ 7.47589, 51.48669 ], [ 7.46397, 51.48392 ] ])
    p = Polygon(p)
    p2 = ([ [ 7.52072, 51.51803 ], [ 7.51858, 51.51722 ], [ 7.52072, 51.51495 ], 
           [ 7.52425, 51.51506 ], [ 7.53244, 51.51528 ], [ 7.53386, 51.51389 ], 
           [ 7.52786, 51.508 ], [ 7.52997, 51.50608 ], [ 7.53503, 51.50153 ], 
           [ 7.54314, 51.50328 ], [ 7.54381, 51.50145 ], [ 7.54011, 51.4992 ], 
           [ 7.54297, 51.49642 ], [ 7.55839, 51.49947 ], [ 7.55125, 51.50597 ], 
           [ 7.55439, 51.51011 ], [ 7.55881, 51.51595 ], [ 7.56322, 51.51772 ], 
           [ 7.56206, 51.51908 ], [ 7.56039, 51.52097 ], [ 7.55597, 51.521 ], 
           [ 7.55492, 51.52169 ], [ 7.55239, 51.52333 ], [ 7.54136, 51.52161 ], 
           [ 7.53736, 51.52492 ], [ 7.53633, 51.52578 ], [ 7.53047, 51.52536 ], 
           [ 7.52817, 51.52081 ], [ 7.52072, 51.51803 ] ])
    p2 = Polygon(p2)
    gdf = gpd.GeoDataFrame(index=[0,1], crs='wgs84', geometry=[p,p2])
    gdf.insert(0, "value", [1,1])
    vis = gdf.explore(column = "value",
        cmap = "viridis",
        vmin = 0, 
        vmax = 1)
    vis.save("test.html")

def conv_to_list(geom):

    xx, yy = geom.exterior.coords.xy

    return [[[x, y] for x, y in zip(xx.tolist(), yy.tolist())]]


def read_prepare_data(filepath):

    gdf = pd.read_csv(filepath)
    
    gdf['geometry'] = gdf['geometry'].apply(wkt.loads)
    gdf = gpd.GeoDataFrame(gdf, crs='epsg:25832')
    gdf.to_crs("wgs84", inplace=True)

    gdf["geom"] = gdf["geometry"].apply(conv_to_list)

    return gdf


if __name__ == "__main__":

    cities = ["Aachen", "Dortmund", "Dresden", "Leipzig", "Mannheim", "Münster", "München", "Utrecht"] # enter the paths to the files with the scores here
    #cities = ["Aachen"]
    percentages = ["100"]

    for city in cities:
        for percentage in percentages:
            filepath = f"../input/{city}/data/{percentage}percent.csv"

            gdf = read_prepare_data(filepath)

            gdf = add_color_to_data(
                data=gdf,
                min_value=gdf["score"].min(),
                max_value=gdf["score"].max(),
                value_col="score")

            deck = create_poylgon_pydeck(
                city = city,
                data=gdf,
                tooltip={"text": "Score: {score}"})

            filename = f"../input/{city}/Maps/{percentage}percent" # enter the filename here (without .html)
            deck.to_html(filename + ".html")

