from shiny import App, ui, render, reactive
import geopandas as gpd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.io.img_tiles import OSM, GoogleTiles
from matplotlib_scalebar.scalebar import ScaleBar
from pathlib import Path
import tempfile

# --------- GADM data loading (Niger) -----------
gadm0 = gpd.read_file(Path(__file__).parent / "gadm41_NER_0.json")
gadm1 = gpd.read_file(Path(__file__).parent / "gadm41_NER_1.json")
gadm2 = gpd.read_file(Path(__file__).parent / "gadm41_NER_2.json")
gadm3 = gpd.read_file(Path(__file__).parent / "gadm41_NER_3.json")
country_list = ["Niger"]

# Map inset positions and continent extents
inset_positions = {
    "upper right": [0.7, 0.6, 0.2, 0.2],
    "bottom right": [0.7, 0.1, 0.2, 0.2],
}
continentcoord = {"Africa": [-20, 55, -35, 37]}


class GoogleHybrid(GoogleTiles):
    def _image_url(self, tile):
        x, y, z = tile
        return f"https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"


last_error_message = ""


def get_tiler(basemap_name):
    return GoogleHybrid() if basemap_name == "Google Hybrid" else OSM()


def create_map(
    country,
    region,
    department,
    municipality,
    inset_pos="upper right",
    title="Study Area Map",
    basemap="OSM",
):
    global last_error_message
    try:
        geometry = None
        label_text = ""
        continent = "Africa"

        # Use the most detailed selection
        if municipality:
            gdf_info = gadm3[gadm3["NAME_3"] == municipality]
            label_text = municipality
        elif department:
            gdf_info = gadm2[gadm2["NAME_2"] == department]
            label_text = department
        elif region:
            gdf_info = gadm1[gadm1["NAME_1"] == region]
            label_text = region
        elif country:
            gdf_info = gadm0[gadm0["COUNTRY"] == country]
            label_text = country
        else:
            last_error_message = "Please select a study area."
            return None

        if gdf_info.empty:
            last_error_message = "No geometry to display."
            return None

        geometry = gdf_info["geometry"]
        minx, miny, maxx, maxy = geometry.total_bounds

        fig = plt.figure(figsize=(12, 8), dpi=150)
        ax = plt.axes(projection=ccrs.PlateCarree())
        tiler = get_tiler(basemap)
        ax.add_image(tiler, 7)
        ax.set_extent([minx - 0.1, maxx + 0.1, miny - 0.1, maxy + 0.1])
        geometry.plot(
            ax=ax,
            edgecolor="red",
            facecolor="none",
            linewidth=2,
            transform=ccrs.PlateCarree(),
        )

        for geom in geometry:
            pt = geom.representative_point()
            ax.text(
                pt.x,
                pt.y,
                label_text,
                ha="center",
                fontsize=9,
                bbox=dict(facecolor="white", alpha=0.6),
                transform=ccrs.PlateCarree(),
            )

        ax.add_feature(cfeature.BORDERS, linestyle=":", edgecolor="black")
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
        ax.gridlines(draw_labels=True, linewidth=0.5, color="gray", alpha=0.5)
        ax.add_artist(ScaleBar(1, units="km", location="lower left"))
        ax.annotate(
            "N",
            xy=(0.1, 0.9),
            xytext=(0.1, 0.8),
            arrowprops=dict(facecolor="black", width=5, headwidth=15),
            ha="center",
            va="center",
            fontsize=12,
            xycoords=ax.transAxes,
        )

        plt.title(title, fontsize=13, weight="bold")

        # Inset
        continent_extent = continentcoord["Africa"]
        inset_ax = fig.add_axes(
            inset_positions[inset_pos], projection=ccrs.PlateCarree()
        )
        inset_ax.set_extent(continent_extent)
        inset_tiler = OSM()
        inset_ax.add_image(inset_tiler, 2)
        inset_ax.add_feature(cfeature.BORDERS, linestyle=":", edgecolor="black")
        inset_ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
        gadm0[gadm0["COUNTRY"] == country].plot(
            ax=inset_ax,
            edgecolor="red",
            facecolor="none",
            linewidth=2,
            transform=ccrs.PlateCarree(),
        )

        output_dir = Path(tempfile.gettempdir()) / "study_area_app"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "map_preview.png"
        plt.savefig(output_file, bbox_inches="tight", dpi=150)
        plt.close()
        return output_file

    except Exception as e:
        import traceback

        traceback.print_exc()
        last_error_message = str(e)
        return None


# UI
app_ui = ui.page_fluid(
    ui.panel_title("🗺️ Study Area Map Generator"),
    ui.layout_columns(
        ui.card(
            ui.input_select(
                "country",
                "🌍 Select a Country:",
                choices=country_list,
                selected="Niger",
            ),
            ui.input_select("region", "Region:", choices=[""]),
            ui.input_select("department", "Department:", choices=[""]),
            ui.input_select("municipality", "Municipality:", choices=[""]),
            ui.input_select("zoom_radius", "🔍 Zoom Radius (degrees):", choices=[0.05, 0.1, 0.5, 1, 1.5, 2], selected=1),
            ui.input_radio_buttons(
                "inset",
                "👁️ Inset map position:",
                choices=list(inset_positions.keys()),
                selected="upper right",
            ),
            ui.input_text("title", "📝 Map title:", value="Fig. 1 Study Area Map"),
            ui.input_radio_buttons(
                "basemap_source",
                "🗺️ Select Basemap:",
                choices=["OSM", "Google Hybrid"],
                selected="OSM",
            ),
            ui.input_action_button(
                "update", "📊 Generate Map", class_="btn btn-primary mt-2"
            ),
            ui.markdown("**💬 Credits:** Souleymane Maman Nouri Souley"),
            ui.markdown("[👥 LinkedIn Profile](www.linkedin.com/in/souleymanemamannourisouley)"),
            ui.markdown("[📄 GitHub Profile](https://github.com/halieute")
            ui.markdown("📧 Email: ssouley@uta.cv"),
            class_="p-3 border shadow-sm bg-light",
            class_="p-3 border shadow-sm bg-light",
            width=4,
        ),
        ui.card(
            ui.output_image("map_output"),
            ui.output_ui("message_output"),
            class_="p-3 border shadow-sm bg-white",
            width=8,
        ),
    ),
)


def server(input, output, session):
    @reactive.effect
    @reactive.event(input.country)
    def update_regions():
        country = input.country()
        if country:
            regions = sorted(gadm1[gadm1["COUNTRY"] == country]["NAME_1"].unique())
            ui.update_select("region", choices=[""] + regions, selected="")
        else:
            ui.update_select("region", choices=[""], selected="")

    @reactive.effect
    @reactive.event(input.region)
    def update_departments():
        region = input.region()
        if region:
            departments = sorted(gadm2[gadm2["NAME_1"] == region]["NAME_2"].unique())
            ui.update_select("department", choices=[""] + departments, selected="")
        else:
            ui.update_select("department", choices=[""], selected="")

    @reactive.effect
    @reactive.event(input.department)
    def update_municipalities():
        department = input.department()
        if department:
            municipalities = sorted(
                gadm3[gadm3["NAME_2"] == department]["NAME_3"].unique()
            )
            ui.update_select("municipality", choices=[""] + municipalities, selected="")
        else:
            ui.update_select("municipality", choices=[""], selected="")

    selected_country = reactive.Value("Niger")
    selected_region = reactive.Value("")
    selected_department = reactive.Value("")
    selected_municipality = reactive.Value("")
    selected_inset = reactive.Value("upper right")
    selected_title = reactive.Value("Fig. 1 Study Area Map")
    selected_basemap = reactive.Value("OSM")

    @reactive.effect
    @reactive.event(input.update)
    def _():
        selected_country.set(input.country())
        selected_region.set(input.region())
        selected_department.set(input.department())
        selected_municipality.set(input.municipality())
        selected_inset.set(input.inset())
        selected_title.set(input.title())
        selected_basemap.set(input.basemap_source())

    @reactive.Calc
    def current_map():
        return create_map(
            selected_country(),
            selected_region(),
            selected_department(),
            selected_municipality(),
            inset_pos=selected_inset(),
            title=selected_title(),
            basemap=selected_basemap(),
        )

    @output
    @render.image
    def map_output():
        path = current_map()
        if not path or not path.exists() or path.is_dir():
            return None
        return {"src": str(path), "alt": "Generated map", "width": "100%"}

    @output
    @render.ui
    def message_output():
        path = current_map()
        if not path or not path.exists() or path.is_dir():
            return ui.p(
                f"❌ Unable to generate map: {last_error_message}",
                class_="text-danger fw-bold",
            )
        return None


app = App(app_ui, server)
