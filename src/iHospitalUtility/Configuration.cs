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
                Primary = new MudColor("#E9EFEC"),
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
                Primary = new MudColor("#16423C"),
                TextPrimary = new MudColor("#E9EFEC"),
                PrimaryContrastText = new MudColor("#E9EFEC"),
                Secondary = new MudColor("#6A9C89"),
                TextSecondary = new MudColor("#C4DAD2"),
                AppbarBackground = new MudColor("#6A9C89"),
                AppbarText = new MudColor("#E9EFEC"),
            }
        };
    }
}