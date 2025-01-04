using MudBlazor;
using MudBlazor.Utilities;

namespace iHospitalUtility
{
    public class Configuration
    {
        public static MudTheme Theme = new()
        {
            Typography = new Typography
            {
                Default = new Default
                {
                    FontFamily = ["Poppins", "sans-serif"]
                }
            },
            PaletteLight = new PaletteLight
            {
                Primary = new MudColor("#82b59b"),
                TextPrimary = new MudColor("#16423C"),
                PrimaryContrastText = new MudColor("#16423C"),
                Secondary = new MudColor("#6A9C89"),
                Background = new MudColor("#C4DAD2"),
                AppbarBackground = new MudColor("#E9EFEC"),
                AppbarText = new MudColor("#16423C"),
                DrawerText = new MudColor("#E9EFEC"),
                DrawerBackground = new MudColor("#6A9C89"),
            },
            PaletteDark = new PaletteDark
            {
                Primary = new MudColor("#6A9C89"),
                TextPrimary = new MudColor("#E9EFEC"),
                PrimaryContrastText = new MudColor("#E9EFEC"),
                Secondary = new MudColor("#1a7a6d"),
                TextSecondary = new MudColor("#C4DAD2"),
                AppbarBackground = new MudColor("#6A9C89"),
                AppbarText = new MudColor("#E9EFEC"),
                DrawerText = new MudColor("#E9EFEC"),
            }
        };
    }
}
