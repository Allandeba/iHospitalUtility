using System.Text;
using System.Text.Json;
using Blazored.LocalStorage;
using iHospitalUtility.Models;
using iHospitalUtility.Repository.Interfaces;

namespace iHospitalUtility.Repository
{
    public class LocalStorageRepository : ILocalStorageRepository
    {
        private readonly ILocalStorageService _localStorage;
        public LocalStorageRepository(ILocalStorageService localStorage)
        {
            _localStorage = localStorage;
        }

        public async Task SetItemAsync<T>(string itemKey, T value, DateOnly expiresAt)
        {
            string jsonString = JsonSerializer.Serialize(value);
            byte[] byteArray = Encoding.UTF8.GetBytes(jsonString);
            string base64String = Convert.ToBase64String(byteArray);

            var item = new CacheItem
            {
                Value = base64String,
                ExpiresAt = expiresAt,
            };

            await _localStorage.SetItemAsync(itemKey, item);
        }

        public async Task SetItemAsync<T>(string itemKey, T value) =>
            await SetItemAsync(itemKey, value, DateOnly.MaxValue);

        public async Task<T?> GetItemAsync<T>(string itemKey)
        {
            var cachedItem = await _localStorage.GetItemAsync<CacheItem>(itemKey);
            if (cachedItem is not null)
            {
                if (cachedItem.ExpiresAt > DateOnly.FromDateTime(DateTime.Today.Date))
                {
                    if (cachedItem.Value is not null)
                    {
                        var decodedString = Convert.FromBase64String(cachedItem.Value);
                        return JsonSerializer.Deserialize<T>(decodedString);
                    }
                }

                await RemoveItemAsync(itemKey);
            }

            return default;
        }

        public async Task RemoveItemAsync(string itemKey) =>
            await _localStorage.RemoveItemAsync(itemKey);
    }
}
