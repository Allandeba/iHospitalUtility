using Microsoft.AspNetCore.Components.Web;
using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using iHospitalUtility;
using MudBlazor.Services;
using Blazored.LocalStorage;
using iHospitalUtility.Repository.Interfaces;
using iHospitalUtility.Repository;
using iHospitalUtility.Services.Interfaces;
using iHospitalUtility.Services;

var builder = WebAssemblyHostBuilder.CreateDefault(args);
builder.RootComponents.Add<App>("#app");
builder.RootComponents.Add<HeadOutlet>("head::after");

builder.Services.AddScoped(sp => new HttpClient { BaseAddress = new Uri(builder.HostEnvironment.BaseAddress) });

builder.Services.AddScoped<ILocalStorageRepository, LocalStorageRepository>();
builder.Services.AddScoped<IGestationalAgeService, GestationalAgeService>();

builder.Services.AddMudServices();
builder.Services.AddBlazoredLocalStorage();

await builder.Build().RunAsync();
