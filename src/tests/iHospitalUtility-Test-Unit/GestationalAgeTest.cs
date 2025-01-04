using Moq;
using iHospitalUtility.Models;
using iHospitalUtility.Services;

namespace iHospitalUtility_Test_Unit;

public class GestationalAgeTest
{
    private readonly GestationalAgeService _gestationalAgeService;
    public GestationalAgeTest()
    {
        _gestationalAgeService = new Mock<GestationalAgeService>().Object;
    }

    [Theory]
    [InlineData(9, 26, 1, 27, 3)]
    [InlineData(51, 29, 5, 37, 0)]
    [InlineData(59, 26, 1, 34, 4)]
    [InlineData(20, 25, 5, 28, 4)]
    [InlineData(47, 28, 1, 34, 6)]
    [InlineData(14, 27, 5, 29, 5)]
    public void ShouldReturnExactlyResult(
        int daysSinceBirth,
        int gestationalWeeks,
        int gestationalDays,
        int correctedWeeks,
        int correctedDays)
    {
        var birthDate = DateTime.Today.AddDays(-daysSinceBirth);
        var gestationalAgeParams = new GestacionalAgeParams()
        {
            GestationalWeeks = gestationalWeeks,
            GestationalDays = gestationalDays,
            BirthDate = birthDate,
        };

        var result = _gestationalAgeService.GetCorrectAge(gestationalAgeParams);
        Assert.Equal(correctedWeeks, result.CorrectedWeeks);
        Assert.Equal(correctedDays, result.CorrectedDays);
    }

    [Theory]
    [InlineData(9, 26, 1, "27 semanas e 3 dias")]
    [InlineData(51, 29, 5, "37 semanas e 0 dias")]
    [InlineData(59, 26, 1, "34 semanas e 4 dias")]
    [InlineData(20, 25, 5, "28 semanas e 4 dias")]
    [InlineData(47, 28, 1, "34 semanas e 6 dias")]
    [InlineData(14, 27, 5, "29 semanas e 5 dias")]
    [InlineData(34, 37, 2, "40 semanas a termo e 15 dias")]
    [InlineData(31, 40, 2, "40 semanas a termo e 33 dias")]
    public void ShouldReturnExactlyDisplayResult(
        int daysSinceBirth,
        int gestationalWeeks,
        int gestationalDays,
        string displayResult)
    {
        var birthDate = DateTime.Today.AddDays(-daysSinceBirth);
        var gestationalAgeParams = new GestacionalAgeParams()
        {
            GestationalWeeks = gestationalWeeks,
            GestationalDays = gestationalDays,
            BirthDate = birthDate,
        };

        var result = _gestationalAgeService.GetCorrectAge(gestationalAgeParams);

        Assert.Equal(displayResult, result.DisplayResult());
    }
}
